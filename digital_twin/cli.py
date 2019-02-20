# -*- coding: utf-8 -*-

"""Console script for digital_twin."""
import sys
import click

import digital_twin.server



@click.group()
def cli(args=None):
    """Digital twin simulation."""
    click.echo("Replace this message by putting your code into "
               "digital_twin.cli.main")
    click.echo("See click documentation at http://click.pocoo.org/")
    return 0

@cli.command()
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=8080, type=int)
@click.option('--debug/--no-debug', default=False)
def serve(host, port, debug, args=None):
    """Run a flask server with the backend code"""
    app = digital_twin.server.app
    app.run(host=host, debug=debug, port=port)

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
