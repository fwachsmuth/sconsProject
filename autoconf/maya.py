from ._external import *

maya = HeaderChecker('maya', 'maya/MGlobal.h', 'c++', libs=['OpenMaya','Foundation','OpenMayaUI','OpenMayaAnim', 'OpenMayaRender', 'OpenMayaFX'], defines=['_BOOL','REQUIRE_IOSTREAM', 'UNAME', 'LINUX'])

