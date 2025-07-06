/*
Loading Animation
*/
const showLoadingSpinnerWithCaption = (caption) => {
    document.querySelector('.loading-caption').innerHTML = caption;
    document.querySelector('.loading').style.display = 'flex';
    showOverlay();
};

const showLoadingSpinner = () => {
    showLoadingSpinnerWithCaption('');
};

const hideLoadingSpinner = () => {
    document.querySelector('.loading-caption').innerHTML = '';
    document.querySelector('.loading').style.display = 'none';
    hideOverlay();
};

/*
Overlay 
*/
const showOverlay = () => {
    document.querySelector('.overlay').style.display = 'block';
};

const hideOverlay = () => {
    document.querySelector('.overlay').style.display = 'none';
};
