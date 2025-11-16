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

// Store rotation state and image path for preview dialog
let previewImageRotation = 0;
let previewImagePath = '';

/**
 * Shows the preview image dialog with the given image URL and path.
 */
const showPreviewImageDialog = (previewImageUrl, imagePath) => {
    const dialog = document.getElementById('preview-image-dialog');
    dialog.showModal();
    showOverlay();

    const img = dialog.querySelector('img');
    img.src = previewImageUrl;

    // Store image path and reset rotation state
    previewImagePath = imagePath;
    previewImageRotation = 0;
    img.style.transform = 'rotate(0deg)';

    // Enable/disable rotate button based on file type
    const rotateBtn = dialog.querySelector('button[onclick="handleRotateImage()"]');
    const saveBtn = dialog.querySelector('button[onclick="handleSaveImageRotation()"]');
    const isJpeg = isJpegFile(previewImagePath);
    rotateBtn.disabled = !isJpeg;
    saveBtn.disabled = !isJpeg;
}

/**
 * Handles rotation button click - rotates image 90 degrees clockwise
 */
const handleRotateImage = () => {
    const dialog = document.getElementById('preview-image-dialog');
    const img = dialog.querySelector('img');

    // Increment rotation by 90 degrees (0 → 90 → 180 → 270 → 0)
    previewImageRotation = (previewImageRotation + 90) % 360;
    img.style.transform = `rotate(${previewImageRotation}deg)`;
}

/**
 * Handles save button click - sends rotation request to backend
 */
const handleSaveImageRotation = async () => {
    // Validate file is JPG/JPEG
    if (!isJpegFile(previewImagePath)) {
        alert('Rotation is only supported for JPG/JPEG images.');
        return;
    }

    if (previewImageRotation === 0) {
        // No rotation to save, just close
        hidePreviewImageDialog();
        return;
    }

    try {
        const resp = await fetch('/rotate-image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                path: previewImagePath,
                rotation: previewImageRotation
            }),
        });

        const data = await resp.json();
        if (data.status === 'ok') {
            // Update file system snapshot with the new path (treat as a MOVE)
            const oldPath = removeAlbumsPrefix(previewImagePath);
            const newPath = removeAlbumsPrefix(data.newPath);
            updateFileSystem(fileSystemSnapshot, oldPath, newPath);
            updateFileSystemUI();

            hidePreviewImageDialog();
        } else {
            alert(`Failed to save rotation: ${data.message || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error saving rotation:', error);
        alert('Failed to save rotation. Please try again.');
    }
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

    // Reset rotation state and transform
    previewImageRotation = 0;
    previewImagePath = '';
    img.style.transform = 'rotate(0deg)';
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
