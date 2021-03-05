from setuptools import setup, find_packages

from tachyon.__version__ import __version__


setup(
    name='tachyon3',
    url="https://github.com/delvelabs/tachyon",
    version=__version__,
    packages=find_packages(),
    python_requires='>=3.6.0,<3.9.0',
    package_data={'tachyon': ['data/*.json']},
    entry_points={
        'console_scripts': [
            'tachyon = tachyon.__main__:main'
        ]
    },
    install_requires=[
        'hammertime-http[simhash-py]>=0.8,<0.9',
        'easyinject==0.3',
        'click==7.1.2'
    ],
)
