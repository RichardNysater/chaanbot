import os

import setuptools

current_path = os.path.abspath(os.path.dirname(__file__))

with open("README.md", "r") as fh:
    long_description = fh.read()


def read_file(path_segments):
    """Read a file from the package. Takes a list of strings to join to
    make the path"""
    file_path = os.path.join(current_path, *path_segments)
    with open(file_path) as f:
        return f.read()


def exec_file(path_segments):
    """Execute a single python file to get the variables defined in it"""
    result = {}
    code = read_file(path_segments)
    exec(code, result)
    return result


version = exec_file(("chaanbot", "__init__.py"))["__version__"]

setuptools.setup(
    name="chaanbot",
    version=version,
    author="Richard Nysäter",
    author_email="richard@nysater.org",
    description="A Matrix chat bot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPLv3+",
    url="https://github.com/RichardNysater/chaanbot",
    packages=setuptools.find_packages(exclude=["chaanbot.modules.private"]),
    install_requires=[
        "aiohttp>=3.14.5,<4", "appdirs>=1.4.4,<2", "beautifulsoup4>=4.15.0,<5",
        "matrix-nio>=0.26.0,<0.27", "requests>=2.34.2,<3",
    ],
    extras_require={"ai": ["aiohttp>=3.14.5,<4"]},
    package_data={'chaanbot': ['chaanbot.cfg.sample']},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Communications :: Chat",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    keywords="matrix chat bot",
    python_requires=">=3.11.5",
    entry_points={
        'console_scripts': [
            'chaanbot=chaanbot.start:run',
        ],
    },
)
