/**
 * Meal Plan Controller
 * 
 * Handles the interactive features of the meal plan detail page:
 * - Auto-saving grocery list
 * - Copying share link
 * - Toast notifications
 */
(function() {
    class MealPlanController extends window.Stimulus.Controller {
        // DOM targets that this controller interacts with
        static get targets() { 
            return ["groceryList", "saveStatus", "shareLink"] 
        }
        
        // Values passed from the server via data attributes
        static get values() { 
            return {
                saveUrl: String,  // URL for saving grocery list
                csrfToken: String // Django CSRF token
            }
        }

        // Lifecycle method - called when controller connects to the DOM
        connect() {
            if (this.hasGroceryListTarget) {
                this.setupAutoSave()
            }
        }

        // Sets up auto-save functionality for grocery list
        setupAutoSave() {
            let saveTimeout
            this.groceryListTarget.addEventListener('input', () => {
                clearTimeout(saveTimeout)
                this.saveStatusTarget.textContent = 'Saving...'
                saveTimeout = setTimeout(() => this.saveGroceryList(), 3000)  // 3 second delay
            })
        }

        // Saves grocery list to server
        async saveGroceryList() {
            const data = new FormData()
            data.append('grocery_list', this.groceryListTarget.value)
            
            try {
                const response = await fetch(this.saveUrlValue, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.csrfTokenValue
                    },
                    body: data
                })
                
                if (response.ok) {
                    this.saveStatusTarget.textContent = 'Changes saved'
                    setTimeout(() => {
                        this.saveStatusTarget.textContent = ''
                    }, 2000)
                } else {
                    this.saveStatusTarget.textContent = 'Error saving changes'
                }
            } catch (error) {
                this.saveStatusTarget.textContent = 'Error saving changes'
                console.error('Failed to save grocery list:', error)
            }
        }

        // Copies share link to clipboard
        async copyLink() {
            try {
                await navigator.clipboard.writeText(this.shareLinkTarget.value)
                this.showToast('Link copied to clipboard!')
            } catch (err) {
                this.showToast('Failed to copy link', false)
                console.error('Failed to copy link:', err)
            }
        }

        // Utility method for showing toast notifications
        showToast(message, success = true) {
            const toast = document.createElement('div')
            toast.className = 'position-fixed bottom-0 end-0 p-3'
            toast.style.zIndex = '11'
            toast.innerHTML = `
                <div class="toast align-items-center text-white bg-${success ? 'success' : 'danger'} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="d-flex">
                        <div class="toast-body">
                            <i class="bi bi-${success ? 'check-circle' : 'x-circle'} me-2"></i>${message}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                </div>
            `
            document.body.appendChild(toast)
            const toastEl = new bootstrap.Toast(toast.querySelector('.toast'))
            toastEl.show()
            
            toast.addEventListener('hidden.bs.toast', () => {
                document.body.removeChild(toast)
            })
        }
    }

    // Register controller when Stimulus is available
    if (window.StimulusApp) {
        window.StimulusApp.register("meal-plan", MealPlanController)
    } else {
        console.error("Failed to register MealPlanController: Stimulus not initialized")
    }
})();
