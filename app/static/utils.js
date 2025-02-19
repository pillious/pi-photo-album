const clamp = (val, min, max) => Math.min(Math.max(val, min), max);

const getFileExtension = (filename) => filename.split('.').pop().toLowerCase();

const isImageFile = (filename) => ALLOWED_FILE_EXTENSIONS.includes(getFileExtension(filename));

// Returns a list of paths to all the folders.
// If ignoreEmptyFolders is true, folders that contain no files as direct children are not included. Folders that only contain other folders are still included.
const getAlbumPaths = (fileSystem, ignoreEmptyFolders) => {
    const _getAlbumPaths = (fileSystem, ignoreEmptyFolders, stack) => {
        if (fileSystem === null || fileSystem === undefined || fileSystem === '') return [];
        if (!ignoreEmptyFolders && Object.keys(fileSystem).length === 0) return [stack.join('/')];

        let added = false;
        let paths = [];
        for (const [key, val] of Object.entries(fileSystem)) {
            if (typeof val === 'object') {
                paths = [...paths, ..._getAlbumPaths(val, ignoreEmptyFolders, [...stack, key])];
                // Need this to add folder even if it only contains other folders.
                if (!ignoreEmptyFolders && !added && stack.length > 1) {
                    paths.push(stack.join('/'));
                    added = true;
                }
            } else if (!added) {
                paths.push(stack.join('/'));
                added = true;
            }
        }

        return paths;
    };

    return _getAlbumPaths(fileSystem, ignoreEmptyFolders, []);
};
