/**
 * register.js — Photo upload drag & drop + form validation
 */
'use strict';

const dropZone      = document.getElementById('dropZone');
const fileInput     = document.getElementById('photos');
const dropZoneInner = document.getElementById('dropZoneInner');
const previewGrid   = document.getElementById('previewGrid');
const previewThumbs = document.getElementById('previewThumbs');
const photoCount    = document.getElementById('photoCount');
const clearBtn      = document.getElementById('clearPhotos');
const submitBtn     = document.getElementById('submitBtn');
const submitInner   = document.getElementById('submitInner');
const submitLoader  = document.getElementById('submitLoader');

let selectedFiles = [];

fileInput.addEventListener('change', (e) => addFiles(Array.from(e.target.files)));

dropZone.addEventListener('dragover',  (e) => { e.preventDefault(); dropZone.classList.add('dragging'); });
dropZone.addEventListener('dragleave', ()  => dropZone.classList.remove('dragging'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault(); dropZone.classList.remove('dragging');
  addFiles(Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/')));
});

function addFiles(newFiles) {
  const remaining = 10 - selectedFiles.length;
  const toAdd = newFiles.slice(0, remaining);
  if (newFiles.length > remaining) showToast(`Max 10 photos. Added ${toAdd.length}.`, 'warning');
  toAdd.forEach(file => {
    if (!['image/jpeg','image/png','image/webp'].includes(file.type)) {
      showToast(`"${file.name}" is not valid.`, 'error'); return;
    }
    selectedFiles.push(file);
  });
  syncFilesToInput();
  renderPreviews();
}

function syncFilesToInput() {
  const dt = new DataTransfer();
  selectedFiles.forEach(f => dt.items.add(f));
  fileInput.files = dt.files;
}

function renderPreviews() {
  if (selectedFiles.length === 0) {
    dropZoneInner.style.display = 'flex';
    previewGrid.style.display   = 'none';
    return;
  }
  dropZoneInner.style.display = 'none';
  previewGrid.style.display   = 'block';
  photoCount.textContent = `${selectedFiles.length} photo${selectedFiles.length !== 1 ? 's' : ''} selected`;
  previewThumbs.innerHTML = '';
  selectedFiles.forEach((file, index) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const wrap = document.createElement('div');
      wrap.className = 'thumb-wrap';
      wrap.innerHTML = `<img src="${e.target.result}" alt="Photo ${index+1}" loading="lazy"/>
        <button type="button" class="thumb-remove" data-index="${index}"><i class="bi bi-x"></i></button>`;
      wrap.querySelector('.thumb-remove').addEventListener('click', () => removeFile(index));
      previewThumbs.appendChild(wrap);
    };
    reader.readAsDataURL(file);
  });
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  syncFilesToInput();
  renderPreviews();
}

clearBtn.addEventListener('click', () => {
  selectedFiles = []; fileInput.value = ''; renderPreviews();
});

document.getElementById('registrationForm').addEventListener('submit', function(e) {
  const errors = [];
  const name   = document.getElementById('name').value.trim();
  const roll   = document.getElementById('roll_number').value.trim();
  const email  = document.getElementById('email').value.trim();
  const dept   = document.getElementById('department').value;
  const year   = document.getElementById('year').value;

  if (!name || name.length < 3)      errors.push('Full name must be at least 3 characters.');
  if (!roll)                          errors.push('Roll number is required.');
  if (!email || !email.includes('@')) errors.push('Valid email is required.');
  if (!dept)                          errors.push('Please select a department.');
  if (!year)                          errors.push('Please select a year.');
  if (selectedFiles.length === 0)     errors.push('Upload at least 1 face photo.');

  if (errors.length > 0) {
    e.preventDefault();
    errors.forEach(err => showToast(err, 'error'));
    return;
  }
  submitInner.style.display = 'none';
  submitLoader.style.display = 'flex';
  submitBtn.disabled = true;
});

document.getElementById('roll_number').addEventListener('input', function() {
  this.value = this.value.toUpperCase();
});
