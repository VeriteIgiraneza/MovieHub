// Sort functionality
function updateSort(value) {
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('sort', value);
    window.location.href = currentUrl.toString();
}

// Movie details toggle
function toggleDetails(button) {
    const card = button.closest('.movie-card');
    const content = card.querySelector('.collapsible-content');
    const isExpanded = content.classList.toggle('expanded');
    button.textContent = isExpanded ? 'Hide Details' : 'Show Details';
}

// Search type toggle
function showSearch(type) {
    const textSearch = document.getElementById('text-search');
    const filterSearch = document.getElementById('filter-search');
    const buttons = document.querySelectorAll('.tab-btn');

    if (type === 'text') {
        textSearch.classList.remove('hidden');
        filterSearch.classList.add('hidden');
        buttons[0].classList.add('active');
        buttons[1].classList.remove('active');
    } else {
        textSearch.classList.add('hidden');
        filterSearch.classList.remove('hidden');
        buttons[0].classList.remove('active');
        buttons[1].classList.add('active');
    }
}

// Modal functions
function openModal() {
    const modal = document.getElementById('addMovieModal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal() {
    const modal = document.getElementById('addMovieModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function openEditModal(movieId, title, runtime, metascore, plot, directors, stars, rating, votes, gross) {
    const modal = document.getElementById('editMovieModal');
    const form = modal.querySelector('form');

    // Set the form action
    form.action = `/edit_movie/${movieId}`;

    // Populate form fields
    form.querySelector('[name="title"]').value = title;
    form.querySelector('[name="runtime"]').value = runtime;
    form.querySelector('[name="metascore"]').value = metascore;
    form.querySelector('[name="plot"]').value = plot;
    form.querySelector('[name="directors"]').value = directors;
    form.querySelector('[name="stars"]').value = stars;
    form.querySelector('[name="rating"]').value = rating;
    form.querySelector('[name="votes"]').value = votes;
    form.querySelector('[name="gross"]').value = gross ? gross.replace('$', '').replace(/,/g, '') : '';

    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeEditModal() {
    const modal = document.getElementById('editMovieModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

function showDeleteConfirmModal(movieId, movieTitle) {
    const modal = document.getElementById('deleteConfirmModal');
    const form = document.getElementById('deleteMovieForm');
    const modalBody = modal.querySelector('.modal-body');

    // Update form action
    form.action = `/delete_movie/${movieId}`;

    // Update confirmation message
    modalBody.innerHTML = `
        <p>Are you sure you want to delete "${movieTitle}"?</p>
        <p>This action cannot be undone.</p>
    `;

    // Show modal
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeDeleteConfirmModal() {
    const modal = document.getElementById('deleteConfirmModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Dashboard specific function
function toggleEdit(movieId) {
    const viewDiv = document.getElementById(`view-${movieId}`);
    const editForm = document.getElementById(`edit-${movieId}`);

    if (viewDiv.classList.contains('hidden')) {
        viewDiv.classList.remove('hidden');
        editForm.classList.add('hidden');
    } else {
        viewDiv.classList.add('hidden');
        editForm.classList.remove('hidden');
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Modal handling - single window.onclick handler
    window.onclick = function(event) {
        const addModal = document.getElementById('addMovieModal');
        const editModal = document.getElementById('editMovieModal');
        const deleteModal = document.getElementById('deleteConfirmModal');

        if (event.target === addModal) {
            closeModal();
        }
        if (event.target === editModal) {
            closeEditModal();
        }
        if (event.target === deleteModal) {
            closeDeleteConfirmModal();
        }
    };

    // Escape key handling for all modals
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModal();
            closeEditModal();
            closeDeleteConfirmModal();
        }
    });

    // Error message modal handling
    const errorMessage = document.getElementById('error-message');
    const isAddMovieError = errorMessage && errorMessage.dataset.context === 'add-movie';
    const hasFormData = document.querySelector('[name="form_data"]');
    if (isAddMovieError || hasFormData) {
        openModal();
    } else {
        closeModal();
    }

    // Flash messages handling
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.remove();
        }, 5500);

        message.addEventListener('click', () => {
            message.style.animation = 'fadeOut 0.3s ease-out forwards';
            setTimeout(() => {
                message.remove();
            }, 300);
        });
    });
});

// Close add movie modal on homepage
if (window.location.pathname === '/') {
    closeModal();
}