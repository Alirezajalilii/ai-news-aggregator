"""
AI News Aggregator - Main Entry Point
CLI application for running the news aggregation system
"""

import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import load_config, get_config
from src.database.models import init_db, close_db
from src.workers.scraper_worker import ScraperWorker
from src.workers.digest_worker import DigestWorker
from src.services.scheduler import get_scheduler

console = Console()


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/app.log")
        ]
    )


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Path to config file")
@click.option("--log-level", "-l", default="INFO", help="Logging level")
@click.pass_context
def cli(ctx, config, log_level):
    """AI News Aggregator - News aggregation and publishing system"""
    ctx.ensure_object(dict)
    
    # Setup
    setup_logging(log_level)
    
    try:
        config_path = Path(config)
        if config_path.exists():
            load_config(str(config_path))
            ctx.obj["config"] = get_config()
        else:
            console.print(f"[yellow]Warning: Config file not found: {config}[/yellow]")
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
async def init(ctx):
    """Initialize database tables"""
    console.print("[cyan]Initializing database...[/cyan]")
    
    try:
        await init_db()
        console.print("[green]Database initialized successfully![/green]")
    except Exception as e:
        console.print(f"[red]Error initializing database: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--source", "-s", help="Scrape specific source only")
@click.pass_context
async def scrape(ctx, source):
    """Scrape news from all configured sources"""
    console.print("[cyan]Starting scrape...[/cyan]")
    
    worker = ScraperWorker()
    
    try:
        stats = await worker.run()
        
        # Display results
        table = Table(title="Scrape Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Sources Processed", str(stats["sources_processed"]))
        table.add_row("Sources Failed", str(stats["sources_failed"]))
        table.add_row("Articles Scraped", str(stats["articles_scraped"]))
        table.add_row("Articles Saved", str(stats["articles_saved"]))
        table.add_row("Duplicates Skipped", str(stats["articles_duplicate"]))
        table.add_row("Duration", f"{stats.get('duration_seconds', 0):.2f}s")
        
        console.print(table)
        
        if stats["errors"]:
            console.print("\n[yellow]Errors:[/yellow]")
            for err in stats["errors"]:
                console.print(f"  - {err}")
    
    except Exception as e:
        console.print(f"[red]Error during scrape: {e}[/red]")
        sys.exit(1)
    
    finally:
        await worker.close_session()


@cli.command()
@click.option("--category", "-c", multiple=True, help="Filter by category")
@click.pass_context
async def digest(ctx, category):
    """Send news digest to subscribers"""
    console.print("[cyan]Sending digest...[/cyan]")
    
    worker = DigestWorker()
    
    try:
        stats = await worker.run(category_filter=list(category) if category else None)
        
        # Display results
        table = Table(title="Digest Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Subscribers Notified", str(stats["subscribers_notified"]))
        table.add_row("Messages Sent", str(stats["messages_sent"]))
        table.add_row("Articles Included", str(stats["articles_included"]))
        table.add_row("Duration", f"{stats.get('duration_seconds', 0):.2f}s")
        
        console.print(table)
        
        if stats["errors"]:
            console.print("\n[yellow]Errors:[/yellow]")
            for err in stats["errors"]:
                console.print(f"  - {err}")
    
    except Exception as e:
        console.print(f"[red]Error sending digest: {e}[/red]")
        sys.exit(1)
    
    finally:
        await worker.close_session()


@cli.command()
@click.pass_context
async def scheduler(ctx):
    """Start the scheduler for periodic tasks"""
    console.print("[cyan]Starting scheduler...[/cyan]")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]")
    
    scheduler = get_scheduler()
    scheduler.start()
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping scheduler...[/yellow]")
        scheduler.stop()


@cli.command()
@click.argument("job_name")
@click.pass_context
async def run_job(ctx, job_name):
    """Run a specific job immediately"""
    scheduler = get_scheduler()
    
    try:
        await scheduler.run_now(job_name)
        console.print(f"[green]Job '{job_name}' completed![/green]")
    except Exception as e:
        console.print(f"[red]Error running job: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
async def status(ctx):
    """Show system status"""
    config = ctx.obj.get("config")
    
    if not config:
        console.print("[yellow]No config loaded[/yellow]")
        return
    
    table = Table(title="System Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("App Name", config.app.name)
    table.add_row("Version", config.app.version)
    table.add_row("Environment", config.app.environment)
    table.add_row("Database", f"{config.database.host}:{config.database.port}")
    table.add_row("Redis", f"{config.redis.host}:{config.redis.port}")
    table.add_row("Scheduler", "Enabled" if config.scheduler.enabled else "Disabled")
    table.add_row("Sources", str(len([s for s in config.scraper.sources if s.enabled])))
    
    console.print(table)


# Create logs directory
Path("logs").mkdir(exist_ok=True)


if __name__ == "__main__":
    asyncio.run(cli())
