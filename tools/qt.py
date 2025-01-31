
"""SCons.Tool.qt

Tool-specific initialization for Qt.

There normally shouldn't be any need to import this module directly.
It will usually be imported through the generic SCons.Tool.Tool()
selection method.

"""

#
# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010 The SCons Foundation
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__revision__ = "src/engine/SCons/Tool/qt.py 5023 2010/06/14 22:05:46 scons"

import os.path
import re

import SCons.Action
import SCons.Builder
import SCons.Defaults
import SCons.Scanner
import SCons.Tool
import SCons.Util

class ToolQtWarning(SCons.Warnings.SConsWarning):
	pass

class GeneratedMocFileNotIncluded(ToolQtWarning):
	pass

class QtdirNotFound(ToolQtWarning):
	pass

SCons.Warnings.enableWarningClass(ToolQtWarning)

header_extensions = [".h", ".hxx", ".hpp", ".hh"]
if SCons.Util.case_sensitive_suffixes('.h', '.H'):
	header_extensions.append('.H')
# TODO: The following two lines will work when integrated back to SCons
# TODO: Meanwhile the third line will do the work
#cplusplus = __import__('SCons.Tool.c++', globals(), locals(), [])
#cxx_suffixes = cplusplus.CXXSuffixes
cxx_suffixes = [".c", ".cxx", ".cpp", ".cc"]

# this function replace a given pattern (pat) by s_after inside the file fname
def fileReplace(fname, pat, s_after):
    # first, see if the pattern is even in the file.
    with open(fname) as f:
        if not any(re.search(pat, line) for line in f):
            return # pattern does not occur in file so we are done.

    # pattern is in the file, so perform replace operation.
    with open(fname) as f:
        out_fname = fname + ".tmp"
        out = open(out_fname, "w")
        for line in f:
            out.write(re.sub(pat, s_after, line))
        out.close()
        f.close();
        os.remove(fname)
        os.rename(out_fname, fname)

# simplify very long useless includes such as #include "../../../../foo.hpp" with #include "./foo.hpp"
# this is useful because moc generates very long relative includes that implies issues on windows OS.
def simplifyInclude(target, source, env):
    fileReplace(target[0].rstr(), "#include\s+\"(\.\./)+", "#include \"" + os.getcwd().replace("\\", "/") + "/" );
    return None

def checkMocIncluded(target, source, env):
	moc = target[0]
	cpp = source[0]
	# looks like cpp.includes is cleared before the build stage :-(
	# not really sure about the path transformations (moc.cwd? cpp.cwd?) :-/
	path = SCons.Defaults.CScan.path(env, moc.cwd)
	includes = SCons.Defaults.CScan(cpp, env, path)
	if not moc in includes:
		SCons.Warnings.warn(
			GeneratedMocFileNotIncluded,
			"Generated moc file '%s' is not included by '%s'" %
			(str(moc), str(cpp)))

def find_file(filename, paths, node_factory):
	for dir in paths:
		node = node_factory(filename, dir)
		if node.rexists():
			return node
	return None

class _Automoc(object):
	"""
	Callable class, which works as an emitter for Programs, SharedLibraries and
	StaticLibraries.
	"""

	def __init__(self, objBuilderName):
		self.objBuilderName = objBuilderName
		
	def __call__(self, target, source, env):
		"""
		Smart autoscan function. Gets the list of objects for the Program
		or Lib. Adds objects and builders for the special qt files.
		"""
		try:
			if int(env.subst('$QT_AUTOSCAN')) == 0:
				return target, source
		except ValueError:
			pass
		try:
			debug = int(env.subst('$QT_DEBUG'))
		except ValueError:
			debug = 0

		# some shortcuts used in the scanner
		splitext = SCons.Util.splitext
		objBuilder = getattr(env, self.objBuilderName)
  
		# some regular expressions:
		# Q_OBJECT detection
		q_object_search = re.compile(r'[^A-Za-z0-9]Q_OBJECT[^A-Za-z0-9]') 
		# cxx and c comment 'eater'
		#comment = re.compile(r'(//.*)|(/\*(([^*])|(\*[^/]))*\*/)')
		# CW: something must be wrong with the regexp. See also bug #998222
		#	 CURRENTLY THERE IS NO TEST CASE FOR THAT
		
		# The following is kind of hacky to get builders working properly (FIXME)
		objBuilderEnv = objBuilder.env
		objBuilder.env = env
		mocBuilderEnv = env.Moc.env
		env.Moc.env = env
		
		# make a deep copy for the result; MocH objects will be appended
		out_sources = source[:]

		for obj in SCons.Util.flatten(source):
			if not isinstance(obj, SCons.Node.Node) or not obj.has_builder():
				# binary obj file provided
				if debug:
					print("scons: qt: '%s' seems to be a binary. Discarded." % str(obj))
				continue
			cpp = obj.sources[0]
			if not splitext(str(cpp))[1] in cxx_suffixes:
				if debug:
					print("scons: qt: '%s' is no cxx file. Discarded." % str(cpp))
					# c or fortran source
				continue
			#cpp_contents = comment.sub('', cpp.get_text_contents())
			cpp_contents = cpp.get_text_contents()
			h=None
			for h_ext in header_extensions:
				# try to find the header file in the corresponding source
				# directory
				hname = splitext(cpp.name)[0] + h_ext
				h = find_file(hname, (cpp.get_dir(),), env.File)
				if h:
					if debug:
						print("scons: qt: Scanning '%s' (header of '%s')" % (str(h), str(cpp)))
					#h_contents = comment.sub('', h.get_text_contents())
					h_contents = h.get_text_contents()
					break
			if not h and debug:
				print("scons: qt: no header for '%s'." % (str(cpp)))
			if h and q_object_search.search(h_contents):
				# h file with the Q_OBJECT macro found -> add moc_cpp
				moc_cpp = env.Moc(h)
				moc_o = objBuilder(moc_cpp)
				out_sources.append(moc_o)
				#moc_cpp.target_scanner = SCons.Defaults.CScan
				if debug:
					print("scons: qt: found Q_OBJECT macro in '%s', moc'ing to '%s'" % (str(h), str(moc_cpp)))
			if cpp and q_object_search.search(cpp_contents):
				# cpp file with Q_OBJECT macro found -> add moc
				# (to be included in cpp)
				moc = env.Moc(cpp)
				env.Ignore(moc, moc)
				print("scons: qt: found Q_OBJECT macro in '%s', moc'ing to '%s'" % (str(cpp), str(moc)))
				#moc.source_scanner = SCons.Defaults.CScan
		# restore the original env attributes (FIXME)
		objBuilder.env = objBuilderEnv
		env.Moc.env = mocBuilderEnv

		return (target, out_sources)

AutomocShared = _Automoc('SharedObject')
AutomocStatic = _Automoc('StaticObject')

def uicEmitter(target, source, env):
	adjustixes = SCons.Util.adjustixes
	bs = SCons.Util.splitext(str(source[0].name))[0]
	bs = os.path.join(str(target[0].get_dir()),bs)
	# first target (header) is automatically added by builder
	if len(target) < 2:
		# second target is implementation
		target.append(
			#env.File(
				adjustixes(
					bs,
					env.subst('$QT_UICIMPLPREFIX'),
					env.subst('$QT_UICIMPLSUFFIX')
				)
			#)
		)
	#if len(target) < 3:
	#	# third target is moc file
	#	target.append(
	#		#env.File(
	#			adjustixes(
	#				bs,
	#				env.subst('$QT_MOCHPREFIX')+'ui_',#+env.subst('$QT_UICIMPLPREFIX'), # to check
	#				env.subst('$QT_MOCHSUFFIX')#+env.subst('$QT_UICIMPLSUFFIX')
	#			)
	#		#)
	#	)
	#print '-- uicEmitter --'
	#for i in range(len(target)):
	#	if not isinstance( target[i], str ):
	#		print 'target['+str(i)+']', target[i].str_for_display()
	#	else:
	#		print 'target['+str(i)+']', target[i]
	#for i in range(len(source)):
	#	if not isinstance( source[i], str ):
	#		print 'source['+str(i)+']', source[i].str_for_display()
	#	else:
	#		print 'source['+str(i)+']', source[i]
	#print '-- uicEmitter --'
	return target, source

def uicScannerFunc(node, env, path):
	lookout = []
	lookout.extend(env['CPPPATH'])
	lookout.append(str(node.rfile().dir))
	includes = re.findall("<include.*?>(.*?)</include>", node.get_text_contents())
	result = []
	for incFile in includes:
		dep = env.FindFile(incFile,lookout)
		if dep:
			result.append(dep)
	#print 'uicScannerFunc: ', result
	return result

uicScanner = SCons.Scanner.Base(
		uicScannerFunc,
		name = "UicScanner", 
		node_class = SCons.Node.FS.File,
		node_factory = SCons.Node.FS.File,
		recursive = 0
	)

def generate(env):
	"""Add Builders and construction variables for qt to an Environment."""
	CLVar = SCons.Util.CLVar
	Action = SCons.Action.Action
	Builder = SCons.Builder.Builder

	env.SetDefault(
		QT_AUTOSCAN = 1, # scan for moc'able sources

		# Some QT specific flags. I don't expect someone wants to
		# manipulate those ...
		QT_UICIMPLFLAGS = CLVar(''),
		QT_UICDECLFLAGS = CLVar(''),
		QT_MOCFROMHFLAGS = CLVar(''),
		QT_MOCFROMCXXFLAGS = CLVar('-i'),

		# suffixes/prefixes for the headers / sources to generate
		QT_UICDECLPREFIX = '', #'ui_',
		QT_UICDECLSUFFIX = '.h',
		QT_UICIMPLPREFIX = '', #'ui_',
		QT_UICIMPLSUFFIX = '$CXXFILESUFFIX',
		QT_MOCHPREFIX = 'moc_',
		QT_MOCHSUFFIX = '$CXXFILESUFFIX',
		QT_MOCCXXPREFIX = '',
		QT_MOCCXXSUFFIX = '.moc',
		QT_UISUFFIX = '.ui',
                QT4_LUPDATE = os.path.join('$QT_BINPATH','lupdate'),
                QT4_LRELEASE = os.path.join('$QT_BINPATH','lrelease'),
                QT4_LUPDATECOM = '$QT4_LUPDATE $SOURCE -ts $TARGET',
                QT4_LRELEASECOM = '$QT4_LRELEASE $SOURCE',

		# Commands for the qt support ...
		# command to generate header, implementation and moc-file
		# from a .ui file
		QT_UICCOM = [
			CLVar('$QT_UIC $QT_UICDECLFLAGS -o ${TARGETS[0]} $SOURCE'),
			CLVar('$QT_UIC $QT_UICIMPLFLAGS -impl ${TARGETS[0].file} '
				  '-o ${TARGETS[1]} $SOURCE'),
			#CLVar('$QT_MOC $QT_MOCFROMHFLAGS -o ${TARGETS[2]} ${TARGETS[0]}'),
		],
		# command to generate meta object information for a class
		# declarated in a header
		QT_MOCFROMHCOM = (
			  '$QT_MOC $QT_MOCFROMHFLAGS -o ${TARGETS[0]} $SOURCE'
		),
		# command to generate meta object information for a class
		# declarated in a cpp file
		QT_MOCFROMCXXCOM = [
			CLVar('$QT_MOC $QT_MOCFROMCXXFLAGS -o ${TARGETS[0]} $SOURCE'),
                        Action(checkMocIncluded,None), Action(simplifyInclude)]
	)

	# ... and the corresponding builders
	uicBld = Builder(
			action = SCons.Action.Action('$QT_UICCOM', '$QT_UICCOMSTR'),
			emitter = uicEmitter,
			src_suffix = '$QT_UISUFFIX',
			suffix = '$QT_UICDECLSUFFIX',
			prefix = '$QT_UICDECLPREFIX',
			source_scanner = uicScanner,
		)

	mocBld = Builder(action={}, prefix={}, suffix={})
	for h in header_extensions:
		act = SCons.Action.Action('$QT_MOCFROMHCOM', '$QT_MOCFROMHCOMSTR')
		mocBld.add_action(h, act)
		mocBld.prefix[h] = '$QT_MOCHPREFIX'
		mocBld.suffix[h] = '$QT_MOCHSUFFIX'
	for cxx in cxx_suffixes:
		act = SCons.Action.Action('$QT_MOCFROMCXXCOM', '$QT_MOCFROMCXXCOMSTR')
		mocBld.add_action(cxx, act)
		mocBld.prefix[cxx] = '$QT_MOCCXXPREFIX'
		mocBld.suffix[cxx] = '$QT_MOCCXXSUFFIX'

	# register the builders 
	# Translation builder
	tsbuilder = Builder(
		action = SCons.Action.Action('$QT4_LUPDATECOM'), #,'$QT4_LUPDATECOMSTR'),
		multi=1
		)
	qmbuilder = Builder(
		action = SCons.Action.Action('$QT4_LRELEASECOM'),# , '$QT4_LRELEASECOMSTR'),
		src_suffix = '.ts',
		suffix = '.qm',
		single_source = True
		)

	env['BUILDERS']['Ts'] = tsbuilder
	env['BUILDERS']['Qm'] = qmbuilder
	env['BUILDERS']['Uic'] = uicBld
	env['BUILDERS']['Moc'] = mocBld
	static_obj, shared_obj = SCons.Tool.createObjBuilders(env)
	static_obj.add_src_builder('Uic')
	shared_obj.add_src_builder('Uic')

	env.AddMethod( enableQtEmmitters, "EnableQtEmmitters")


def enableQtEmmitters(self):
	# We use the emitters of Program / StaticLibrary / SharedLibrary
	# to scan for moc'able files
	# We can't refer to the builders directly, we have to fetch them
	# as Environment attributes because that sets them up to be called
	# correctly later by our emitter.
	self.AppendUnique(
			PROGEMITTER = [AutomocStatic],
			SHLIBEMITTER = [AutomocShared],
			LIBEMITTER  = [AutomocStatic],
		)

def exists(env):
	return True

