/**
 * Shows the create folder dialog.
 * The dialog is populated with the available album paths.
 */
const showCreateFolderDialog = () => {
    document.getElementById('create-folder-dialog').showModal();
    showOverlay();
    populateAlbumPaths('create-folder-dialog');
};

/**
 * Hides the create folder dialog and resets the form.
 */
const hideCreateFolderDialog = () => {
    document.getElementById('create-folder-dialog').close();
    hideOverlay();

    const form = document.getElementById('create-folder-dialog').querySelector('form');
    form.reset();
};

/** 
 * Shows the copy files dialog.
 * The dialog is populated with the available album paths.
 */
const showCopyFilesDialog = () => {
    document.getElementById('copy-files-dialog').showModal();
    showOverlay();
    populateAlbumPaths('copy-files-dialog');
}

/**
 * Hides the copy files dialog and resets the form.
 */
const hideCopyFilesDialog = () => {
    document.getElementById('copy-files-dialog').close();
    hideOverlay();

    const form = document.getElementById('copy-files-dialog').querySelector('form');
    form.reset();
}

/**
 * Shows the move files dialog.
 * The dialog is populated with the available album paths.
 */
const showMoveFilesDialog = () => {
    document.getElementById('move-files-dialog').showModal();
    showOverlay();
    populateAlbumPaths('move-files-dialog');
}

/**
 * Hides the move files dialog and resets the form.
 */
const hideMoveFilesDialog = () => {
    document.getElementById('move-files-dialog').close();
    hideOverlay();

    const form = document.getElementById('move-files-dialog').querySelector('form');
    form.reset();
}

/**
 * Shows the rename file dialog.
 */
const showRenameFileDialog = () => {
    document.getElementById('rename-file-dialog').showModal();
    showOverlay();

    const form = document.getElementById('rename-file-dialog').querySelector('form');
    form.reset();
}

/**
 * Hides the rename file dialog and resets the form.
 */
const hideRenameFileDialog = () => {
    document.getElementById('rename-file-dialog').close();
    hideOverlay();

    const form = document.getElementById('rename-file-dialog').querySelector('form');
    form.reset();
}

/**
 * Shows the preview image dialog with the given image URL.
 */
const showPreviewImageDialog = (previewImageUrl) =>{
    const dialog = document.getElementById('preview-image-dialog');
    dialog.showModal();
    showOverlay();

    const img = dialog.querySelector('img');
    img.src = previewImageUrl;
}

/**
 * Hides the preview image dialog
 */
const hidePreviewImageDialog = () => {
    const dialog = document.getElementById('preview-image-dialog');
    dialog.close();
    hideOverlay();

    const img = dialog.querySelector('img');
    img.src = '';
}

const populateAlbumPaths = (dialogId) => {
    const albumPaths = removeAlbumsPrefixes(getAlbumPaths(fileSystemSnapshot, false));
    const select = document.getElementById(dialogId).querySelector('select');
    select.innerHTML = select.firstElementChild.outerHTML;
    for (const path of albumPaths) {
        const option = document.createElement('option');
        option.value = path;
        option.innerHTML = path;
        select.appendChild(option);
    }
};
