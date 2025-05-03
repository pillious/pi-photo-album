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

// Equivalent of Werkzeug's secure_filename function in Python
const secureFilename = (filename) => {
    // Normalize Unicode characters to ASCII
    filename = filename.normalize('NFKD').replace(/[\u0300-\u036f]/g, '');

    // Remove non-ASCII characters
    filename = filename.replace(/[^\x00-\x7F]/g, '');

    // Replace path separators with spaces
    filename = filename.replace(/[\/\\]/g, ' ');

    // Remove unwanted characters and replace spaces with underscores
    filename = filename.replace(/[^a-zA-Z0-9._-]/g, '_').replace(/_+/g, '_');

    // Trim leading and trailing dots or underscores
    filename = filename.replace(/^[_\.]+|[_\.]+$/g, '');

    // Handle Windows reserved filenames
    const windowsReservedNames = [
        'CON',
        'PRN',
        'AUX',
        'NUL',
        'COM1',
        'COM2',
        'COM3',
        'COM4',
        'COM5',
        'COM6',
        'COM7',
        'COM8',
        'COM9',
        'LPT1',
        'LPT2',
        'LPT3',
        'LPT4',
        'LPT5',
        'LPT6',
        'LPT7',
        'LPT8',
        'LPT9',
    ];
    const baseName = filename.split('.')[0].toUpperCase();
    if (windowsReservedNames.includes(baseName)) {
        filename = `_${filename}`;
    }

    return filename;
};

/**
 *
 *  A fast and simple 53-bit string hash function with decent collision resistance.
 *
 *  cyrb53 (c) 2018 bryc (github.com/bryc)
 *
 *  License: Public domain (or MIT if needed). Attribution appreciated.
 *
 *  Largely inspired by MurmurHash2/3, but with a focus on speed/simplicity.
 *
 * @param {string} str
 * @param {number} seed
 * @returns {number} A 53-bit hash value.
 */
const cyrb53 = function (str, seed = 0) {
    let h1 = 0xdeadbeef ^ seed,
        h2 = 0x41c6ce57 ^ seed;
    for (let i = 0, ch; i < str.length; i++) {
        ch = str.charCodeAt(i);
        h1 = Math.imul(h1 ^ ch, 2654435761);
        h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
    h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
    h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    return 4294967296 * (2097151 & h2) + (h1 >>> 0);
};

/**
 * Given a deeply nested object this function flattens the object into a list of paths.
 *
 * @param {Object<string, string | Object>} obj deeply nested object whose keys & values are all strings
 * @returns {Array<string>} a list of paths to all the files in the object
 */
const flattenObjectToPaths = (obj) => {
    const helper = (fs, path) => {
        let files = [];
        const pathStr = path.join('/');
        for (const [key, val] of Object.entries(fs)) {
            if (typeof val === 'object') {
                files = files.concat(helper(val, [...path, key]));
            } else {
                files.push(pathStr + '/' + key);
            }
        }
        return files;
    };

    return helper(obj, []);
};

/**
 * Removes the leading 'albums/' prefix from a path string.
 *
 * @param {string} pathStr a path string that may or may not start with 'albums/'
 * @returns the pathStr without the leading 'albums/' prefix
 */
const removeAlbumsPrefix = (pathStr) => {
    if (pathStr.startsWith('albums/')) {
        return pathStr.substring(7);
    }
    return pathStr;
};

/**
 * Removes the leading 'albums/' prefix from each path in a list of paths.
 *
 * @param {Array} paths an array of path strings that may or may not start with 'albums/'
 * @returns an array of path strings without the leading 'albums/' prefix
 */
const removeAlbumsPrefixes = (paths) => paths.map((path) => removeAlbumsPrefix(path));

// const getFolderObjFromPath = (fileSystem, path) => {
//     const pathParts = path.split('/');
//     let loc = fileSystem;
//     for (const part of pathParts) {
//         if (loc[part] === undefined) {
//             return null;
//         }
//         loc = loc[part];
//     }
//     return loc;
// }