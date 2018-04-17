from setuptools import setup, find_packages
from pip.req import parse_requirements

from tachyon.core.__version__ import __version__

reqs = [str(x.req) for x in parse_requirements('./requirements.txt', session=False)]

setup(
    name='tachyon',
    version=__version__,
    packages=find_packages(),
    package_data={'tachyon': ['data/*.json']},
    entry_points={
        'console_scripts': [
            'tachyon = tachyon.__main__:main'
        ]
    },
    install_requires=reqs,
)
