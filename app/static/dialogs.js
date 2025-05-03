/**
 * Shows the create folder dialog.
 * The dialog is populated with the available album paths.
 */
const showCreateFolderDialog = () => {
    document.getElementById('create-folder-dialog').showModal();
    document.querySelector('.overlay').style.display = 'block';

    const albumPaths = removeAlbumsPrefixes(getAlbumPaths(fileSystemSnapshot, false))

    const select = document.getElementById('create-folder-dialog').querySelector('select');
    select.innerHTML = select.firstElementChild.outerHTML;
    for (const path of albumPaths) {
        const option = document.createElement('option');
        option.value = path;
        option.innerHTML = path;
        select.appendChild(option);
    }
};

/**
 * Hides the create folder dialog and resets the form.
 */
const hideCreateFolderDialog = () => {
    document.getElementById('create-folder-dialog').close();
    document.querySelector('.overlay').style.display = 'none';

    const form = document.getElementById('create-folder-dialog').querySelector('form');
    form.reset();
};

/**
 * Shows the move files dialog.
 * The dialog is populated with the available album paths.
 */
const showMoveFilesDialog = () => {
    document.getElementById('move-files-dialog').showModal();
    document.querySelector('.overlay').style.display = 'block';
    
    const albumPaths = removeAlbumsPrefixes(getAlbumPaths(fileSystemSnapshot, false))

    const select = document.getElementById('move-files-dialog').querySelector('select');
    select.innerHTML = select.firstElementChild.outerHTML;
    for (const path of albumPaths) {
        const option = document.createElement('option');
        option.value = path;
        option.innerHTML = path;
        select.appendChild(option);
    }
}

/**
 * Hides the move files dialog and resets the form.
 */
const hideMoveFilesDialog = () => {
    document.getElementById('move-files-dialog').close();
    document.querySelector('.overlay').style.display = 'none';

    const form = document.getElementById('move-files-dialog').querySelector('form');
    form.reset();
}