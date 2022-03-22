#-*- encoding: UTF-8 -*-
from setuptools import setup, find_packages
"""
打包的用的setup必须引入，
"""


VERSION = '1.1.9'

with open('README.md', encoding='utf-8') as fp:
    readme = fp.read()

setup(name='model-log',
      version=VERSION,
      description="test description",
      long_description=readme,
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='python ML DL model log',
      author='mantch',
      author_email='mantchs@163.com',
      url='https://github.com/NLP-LOVE',
      license='MIT',
      packages=['model_log'],
      include_package_data=True,
      zip_safe=True,
      install_requires=[
        'flask >= 0.11'
      ],
      entry_points={
        'console_scripts':[
            'model-log = model_log.modellog_web:main'
        ]
      }
)