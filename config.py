from yaml import load, Loader

with open('config.yml') as f:
    configs = load(f, Loader=Loader)
