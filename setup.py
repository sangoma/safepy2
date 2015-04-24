from setuptools import setup


setup(name='safepy2',
      version='1',
      description='A python wrapper around the SAFe object model',
      author='Simon Gomizelj',
      author_email='sgomizelj@sangoma.com',
      url='http://github.com/sangoma/safepy2',
      packages = ['safe'],
      use_2to3 = True,
      classifiers=['Development Status :: 3 - Alpha',
                   'Intended Audience :: Developers',
                   'Operating System :: POSIX',
                   'Topic :: Utilities',
                   'Programming Language :: Python'])
