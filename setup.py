from setuptools import setup, find_namespace_packages
setup(
    name="MDXtract",
    version="2.1.0",
    scripts=["mdx2syx", "pmd2syx", "pdx2wav", "pmd2wav"],
    packages=find_namespace_packages(),
    package_data={
        "": ["*.md"],
    },
    author="David Lindecrantz",
    author_email="optiroc@gmail.com",
    description="MDXtract is a set of python tools for extracting instrument and sample data from files used by the MXDRV and PMD sound drivers.",
    url="https://github.com/Optiroc/MDXtract",
    license="MIT"
)
