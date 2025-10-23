from setuptools import setup, find_packages

setup(
    name="youtube-history-collector",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "selenium",
        "pytubefix",
        "pandas",
        "requests",
    ],
    entry_points={
        'console_scripts': [
            'collect-youtube-history=src.main:main',
        ],
    },
)
