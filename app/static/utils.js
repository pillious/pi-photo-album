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

// Generates a 128 bit UUID returned as a hex string
// const genUUID = () => {
//     return '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, (c) =>
//         (+c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (+c / 4)))).toString(16)
//     );
// };

// const uuidToBytes = (uuid) => {
//     // Remove dashes
//     const hex = uuid.replace(/-/g, '');
//     // Convert hex to Uint8Array
//     const bytes = new Uint8Array(hex.match(/.{1,2}/g).map((byte) => parseInt(byte, 16)));
//     return bytes
// };
