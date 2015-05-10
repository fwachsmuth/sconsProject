from _external import *
from boost import *
from boost_log import *

tuttleHost = LibWithHeaderChecker(
        'tuttleHost',
        'tuttle/plugin/global.hpp',
        'c++',
        name='tuttleHost',
        dependencies= [boost, boost_log,],
        )


