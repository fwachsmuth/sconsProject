from _external import *
from boost import *

tuttleHost = LibWithHeaderChecker(
        'tuttleHost',
        'tuttle/plugin/global.hpp',
        'c++',
        name='tuttleHost',
        dependencies= [boost],
        )


