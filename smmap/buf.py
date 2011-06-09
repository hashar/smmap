"""Module with a simple buffer implementation using the memory manager"""
from mman import MemoryCursor

import sys

__all__ = ["MappedMemoryBuffer"]

class MappedMemoryBuffer(object):
	"""A buffer like object which allows direct byte-wise object and slicing into 
	memory of a mapped file. The mapping is controlled by the provided cursor.
	
	The buffer is relative, that is if you map an offset, index 0 will map to the 
	first byte at the offset you used during initialization or begin_access"""
	__slots__ = '_c'		# our cursor
	
	
	def __init__(self, cursor = None, offset = 0, size = sys.maxint, flags = 0):
		"""Initalize the instance to operate on the given cursor.
		:param cursor: if not None, the associated cursor to the file you want to access
			If None, you have call begin_access before using the buffer and provide a cursor 
		:param offset: absolute offset in bytes
		:param size: the total size of the mapping. Defaults to the maximum possible size
		:param flags: Additional flags to be passed to os.open
		:raise ValueError: if the buffer could not achieve a valid state"""
		self._c = cursor
		if cursor and not self.begin_access(cursor, offset, size, flags):
			raise ValueError("Failed to allocate the buffer - probably the given offset is out of bounds")
		# END handle offset

	def __del__(self):
		self.end_access()
		
	def __getitem__(self, i):
		c = self._c
		assert c.is_valid()
		if not c.includes_ofs(i):
			c.use_region(i, 1)
		# END handle region usage
		return c.buffer()[i-c.ofs_begin()]
	
	def __getslice__(self, i, j):
		c = self._c
		# fast path, slice fully included - safes a concatenate operation and 
		# should be the default
		assert c.is_valid()
		if (c.ofs_begin() <= i) and (j < c.ofs_end()):
			b = c.ofs_begin()
			return c.buffer()[i-b:j-b]
		else:
			l = j-i					# total length
			ofs = i
			# Keeping tokens in a list could possible be faster, but the list
			# overhead outweighs the benefits (tested) !
			md = str()
			while l:
				c.use_region(ofs, l)
				d = c.buffer()[:l]
				ofs += len(d)
				l -= len(d)
				md += d
			#END while there are bytes to read
			return md
		# END fast or slow path
	#{ Interface
	
	def begin_access(self, cursor = None, offset = 0, size = sys.maxint, flags = 0):
		"""Call this before the first use of this instance. The method was already
		called by the constructor in case sufficient information was provided.
		
		For more information no the parameters, see the __init__ method
		:param path: if cursor is None the existing one will be used. 
		:return: True if the buffer can be used"""
		if cursor:
			self._c = cursor
		#END update our cursor
		
		# reuse existing cursors if possible
		if self._c is not None and self._c.is_associated():
			return self._c.use_region(offset, size, flags).is_valid()
		return False
		
	def end_access(self):
		"""Call this method once you are done using the instance. It is automatically 
		called on destruction, and should be called just in time to allow system
		resources to be freed.
		
		Once you called end_access, you must call begin access before reusing this instance!"""
		if self._c is not None:
			self._c.unuse_region()
		#END unuse region
		
	def cursor(self):
		""":return: the currently set cursor which provides access to the data"""
		return self._c
		
	#}END interface

