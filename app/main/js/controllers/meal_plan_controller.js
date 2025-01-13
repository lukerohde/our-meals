import { Controller } from '@hotwired/stimulus'
import { showToast } from '../../../static/js/utils/toast'

/**
 * Meal Plan Controller
 * 
 * Handles the interactive features of the meal plan detail page:
 * - Auto-saving grocery list
 * - Copying share link
 * - Toast notifications
 */
export default class extends Controller {
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
                showToast('Changes saved', 'success')
                setTimeout(() => {
                    this.saveStatusTarget.textContent = ''
                }, 2000)
            } else {
                this.saveStatusTarget.textContent = 'Error saving changes'
                showToast('Failed to save changes', 'error')
            }
        } catch (error) {
            this.saveStatusTarget.textContent = 'Error saving changes'
            showToast('Failed to save changes', 'error')
            console.error('Failed to save grocery list:', error)
        }
    }

    // Copies share link to clipboard
    async copyLink() {
        try {
            await navigator.clipboard.writeText(this.shareLinkTarget.value)
            showToast('Link copied to clipboard', 'success')
        } catch (err) {
            showToast('Failed to copy link', 'error')
            console.error('Failed to copy link:', err)
        }
    }
}