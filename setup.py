import setuptools


setup_params = dict(
    name='safepy2',
    version='1',
    description='A python wrapper around the SAFe object model',
    author='Simon Gomizelj',
    author_email='sgomizelj@sangoma.com',
    url='http://github.com/sangoma/safepy2',
    packages=setuptools.find_packages(),
    install_requires=['six', 'requests'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    classifiers=['Development Status :: 3 - Alpha',
                 'Intended Audience :: Developers',
                 'Operating System :: POSIX',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3']
)


if __name__ == '__main__':
    setuptools.setup(**setup_params)
