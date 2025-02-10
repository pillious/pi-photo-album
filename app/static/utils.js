const clamp = (val, min, max) => {
    return Math.min(Math.max(val, min), max);
};

// Returns a list of paths to all the folders that contain a file as a direct child.
const getAlbumPaths = (fileSystem, stack = []) => {
    if (
        fileSystem === null ||
        fileSystem === undefined ||
        Object.keys(fileSystem).length === 0 ||
        fileSystem === ''
    )
        return [];
    let added = false;
    let paths = [];
    for (const [key, val] of Object.entries(fileSystem)) {
        if (typeof val === 'object') {
            paths = [...paths, ...getAlbumPaths(val, [...stack, key])];
        } else {
            if (!added) {
                paths.push(stack.join('/'));
                added = true;
            }
        }
    }
    return paths;
};
