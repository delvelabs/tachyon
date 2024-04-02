from setuptools import setup, find_packages

from tachyon.__version__ import __version__


setup(
    name='tachyon3',
    url="https://github.com/delvelabs/tachyon",
    version=__version__,
    packages=find_packages(),
    python_requires='>=3.6.0,<3.13.0',
    package_data={'tachyon': ['data/*.json']},
    entry_points={
        'console_scripts': [
            'tachyon = tachyon.__main__:main'
        ]
    },
    install_requires=[
        'hammertime-http>=0.8,<0.11',
        'simhash==2.1.2',
        'easyinject>=0.3,<0.4',
        'click>=7.1.2,<9'
    ],
)
