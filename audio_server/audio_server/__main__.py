import click
from audio_server import server


@click.group()
@click.option("--host", type=str, default="localhost")
@click.option("--port", type=int, default=5032)
@click.pass_context
def cli(ctx, host, port) -> None:
    ctx.ensure_object(dict)
    ctx.obj["host"] = host
    ctx.obj["port"] = port


@cli.command()
@click.pass_context
def mic(ctx) -> None:
    mic = server.AudioInput()
    with server.make_server(mic, ctx.obj["port"], host=ctx.obj["host"]) as tcp_server:
        tcp_server.serve_forever()



if __name__ == "__main__":
    cli(auto_envvar_prefix='AUDIOSERVER')
