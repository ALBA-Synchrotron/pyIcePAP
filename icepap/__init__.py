# -----------------------------------------------------------------------------
# This file is part of icepap (https://github.com/ALBA-Synchrotron/pyIcePAP)
#
# Copyright 2008-2017 CELLS / ALBA Synchrotron, Bellaterra, Spain
#
# Distributed under the terms of the GNU General Public License,
# either version 3 of the License, or (at your option) any later version.
# See LICENSE.txt for more info.
#
# You should have received a copy of the GNU General Public License
# along with icepap. If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

# TODO: better use the __all__ = [...] structure
from .communication import IcePAPCommunication
from .controller import IcePAPController
from .fwversion import *
from .utils import *

# The version is updated automatically with bumpversion
# Do not update manually
version = '3.2.0'
