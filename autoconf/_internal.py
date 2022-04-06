
from SCons import Variables
from SCons import Environment

from ._base import *

class InternalLibChecker(BaseLibChecker):

	def __init__(self, lib='', name='', includes=[], envFlags={}, dependencies=[], sconsNode=None, addSources=[] ):
		self.libs  = [lib] # the target (name of the library file without prefix or extension)
		if name:
			self.name = name
		else:
			self.name = lib
		self.includes= list(includes) # includes directories
		self.envFlags = envFlags # library specific flags
		self.dependencies = list(dependencies) # all libraries needed by this library (need to be propagated to all targets using this library)
		self.sconsNode = sconsNode # a reference to the scons node object, we can use to use Depends, Alias, etc.
		self.addSources = addSources

	def enabled(self,env,option=None):
		'''Can't disable an internal library.'''
		return True

	def initOptions(self, project, opts):
		'''No options for internal library.'''
		return True
	
	def configure(self, project, env):
		'''
		Add things to the environment.
		'''
		if self.includes:
			env.AppendUnique( CPPPATH = self.includes )
		
		if self.envFlags:
			env.AppendUnique( **(self.envFlags) )

		# we don't set LIBPATH because it's setted by the project
		# all internal libs are compiled in the same directory
		# project.inOutputLib()

		return True

	def postconfigure(self, project, env, level):
		'''Don't check for local lib, so we only add it.'''
		if self.libs:
			env.PrependUnique( LIBS = self.libs )
		if level == 0:
			if self.addSources:
				#print '!'*100
				#print self.name
				#print 'level:', level
				env.Append( ADDSRC = self.addSources )


