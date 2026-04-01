#from babel import frontend as babel
from babel.messages import frontend as babel
from setuptools import setup

setup(name='anketa',
      version='0.1',
      cmdclass = {'extract_messages': babel.extract_messages,
                  'init_catalog': babel.init_catalog,
                  'update_catalog': babel.update_catalog,
                  'compile_catalog': babel.compile_catalog,}
)

