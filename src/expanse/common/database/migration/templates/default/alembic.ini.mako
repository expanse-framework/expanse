[alembic]
# path to migration scripts
# Use forward slashes (/) also on windows to provide an os agnostic path
script_location = ${script_location}

file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d%%(second).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .
