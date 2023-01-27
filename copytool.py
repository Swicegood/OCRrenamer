import shutil

src = '/mnt/y/My Drive/Organizational/Reciepts/Vehicle'
dest = '/home/jaga/tmp'

destination = shutil.copytree(src, dest) 