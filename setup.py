from setuptools import setup, find_packages

from tachyon.__version__ import __version__


setup(
    name='tachyon3',
    version=__version__,
    packages=find_packages(),
    package_data={'tachyon': ['data/*.json']},
    entry_points={
        'console_scripts': [
            'tachyon = tachyon.__main__:main'
        ]
    },
    install_requires=[
        'hammertime-http>=0.5.0,<0.6',
        'easyinject==0.3',
        'click>=6.7,<7'
    ],
)
