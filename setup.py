from setuptools import setup, find_packages
from pip.req import parse_requirements

from tachyon.core.conf import version as VERSION

reqs = [str(x.req) for x in parse_requirements('./requirements.txt', session=False)]

setup(
    name='tachyon',
    version=VERSION,
    packages=[find_packages()],
    package_data={'tachyon': ['data/*.json']},
    entry_points={
        'console_scripts': [
            'tachyon = tachyon.__main__:main'
        ]
    },
    install_requires=reqs,
)
