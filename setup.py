import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="postal-service",
    version="0.0.1",
    author="Kenneth Schiller",
    author_email="kenschiller@gmail.com",
    description="An email server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Kenadia/postal-service",
    packages=setuptools.find_packages(),
    install_requires=[
        'Envelopes==0.4',
    ],
    classifiers=[
    ],
)
