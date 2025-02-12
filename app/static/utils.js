const clamp = (val, min, max) => {
    return Math.min(Math.max(val, min), max);
};

const getFileExtension = (filename) => {
    return filename.split('.').pop().toLowerCase();
}

const isImageFile = (filename) => {
    const ext = getFileExtension(filename);
    return ALLOWED_FILE_EXTENSIONS.includes(ext);
}

// Returns a list of paths to all the folders that contain a file as a direct child.
// If ignoreEmptyFolders is true, folders that contain no files as direct children are not included.
const getAlbumPaths = (fileSystem, ignoreEmptyFolders) => {
    return _getAlbumPaths(fileSystem, ignoreEmptyFolders, []);
};

// Recursive helper function for getAlbumPaths
const _getAlbumPaths = (fileSystem, ignoreEmptyFolders, stack) => {
    if (fileSystem === null || fileSystem === undefined || fileSystem === '') return [];
    if (!ignoreEmptyFolders && Object.keys(fileSystem).length === 0) return [stack.join('/')];

    let added = false;
    let paths = [];
    for (const [key, val] of Object.entries(fileSystem)) {
        if (typeof val === 'object') {
            paths = [...paths, ..._getAlbumPaths(val, ignoreEmptyFolders, [...stack, key])];
        } else {
            if (!added) {
                paths.push(stack.join('/'));
                added = true;
            }
        }
    }
    return paths;
};