#-*- encoding: UTF-8 -*-
from setuptools import setup

with open('README.md', 'r', encoding='utf-8') as file:
    long_description = file.read()


VERSION = '1.1.2'


setup(name='model-log',
      version=VERSION,
      description="test description",
      long_description=long_description,
      long_description_content_type="text/markdown",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='python,machine-learning,deep-learning,metric,loss',
      author='mantch',
      author_email='mantchs@163.com',
      url='https://github.com/NLP-LOVE/Model_Log',
      license='Apache License 2.0',
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
