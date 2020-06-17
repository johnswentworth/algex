import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="algex-johnswentworth",
    version="0.0.1",
    author="John S Wentworth",
    author_email="jwentworth@g.hmc.edu",
    description="High-school algebra for data structures",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/johnswentworth/algex",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
