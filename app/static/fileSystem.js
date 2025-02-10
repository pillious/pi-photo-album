/*
File System Logic
*/
const updateFileSystemUI = (fileStructure) => {
    const fileSystemTreeRoot = document.getElementById('file-system-tree');
    fileSystemTreeRoot.innerHTML = '';

    const stack = [];
    stack.push([fileStructure.albums, 'file-system-tree']);

    while (stack.length > 0) {
        const [fsObj, elemId] = stack.pop();
        const parent = document.getElementById(elemId);
        const parentPath = parent.getAttribute('data-album-path') || '';
        for (const [key, val] of Object.entries(fsObj)) {
            if (typeof val === 'object') {
                // Folder Name List Item
                const folderLi = document.createElement('li');
                folderLi.classList.add('album-name');
                folderLi.innerHTML = key;
                folderLi.setAttribute('data-album-path', parentPath + '/' + key);
                parent.appendChild(folderLi);

                // Folder Sublist
                const folderUl = document.createElement('ul');
                folderUl.id = key;
                folderUl.setAttribute('data-album-path', parentPath + '/' + key);
                folderUl.style.display = 'none'; // Defaults to hiding files
                parent.appendChild(folderUl);

                // Button to hide files in folder
                const hideBtn = document.createElement('button');
                hideBtn.innerHTML = 'Hide';
                hideBtn.classList.add('hide-album-btn');
                hideBtn.onclick = () => {
                    folderUl.style.display = folderUl.style.display === 'none' ? 'block' : 'none';
                    hideBtn.innerHTML = folderUl.style.display === 'none' ? 'Show' : 'Hide';
                };

                // Button to create a subfolder
                const createAlbumBtn = document.createElement('button');
                createAlbumBtn.innerHTML = 'Create Album';
                createAlbumBtn.classList.add('create-album-btn');
                createAlbumBtn.onclick = () => {
                    const albumName = prompt('Enter album name');
                    if (albumName !== null && albumName.trim() !== '' && !(albumName in val)) {
                        val[albumName] = {};
                        updateFileSystemUI(fileStructure);
                    }
                };

                folderLi.appendChild(hideBtn);
                folderLi.appendChild(createAlbumBtn);

                stack.push([val, key]);
            } else {
                const fileLi = document.createElement('li');
                fileLi.innerHTML = key;
                fileLi.setAttribute('data-album-path', parentPath + '/' + key);
                parent.appendChild(fileLi);
            }
        }
    }
};
