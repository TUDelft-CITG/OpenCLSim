# -*- coding: utf-8 -*-

"""Console script for digital_twin."""
import sys
import click

import digital_twin.server



@click.group()
def cli(args=None):
    """Console script for digital_twin."""
    click.echo("Replace this message by putting your code into "
               "digital_twin.cli.main")
    click.echo("See click documentation at http://click.pocoo.org/")
    return 0

@cli.command()
@click.option('--debug/--no-debug', default=False)
def serve(debug, args=None):
    app = digital_twin.serve.app
    app.run(host='0.0.0.0', debug=debug, port=80)

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
