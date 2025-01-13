import { Controller } from "@hotwired/stimulus"
import { showToast } from '../../../static/js/utils/toast'

export default class extends Controller {
  static targets = ["form", "input", "fileInput", "previewContainer", "submit", "loading"]
  static values = {
    uploadUrl: String
  }

  connect() {
    this.uploadedPhotos = []
    this.isProcessing = false

    // Add paste handler to input only
    this.inputTarget.addEventListener('paste', (e) => this.handlePaste(e))
    // Add input listener for expanding textarea
    this.inputTarget.addEventListener('input', this.autoExpand.bind(this))

  }

  disconnect() {
    // Clean up event listeners
    this.inputTarget.removeEventListener('paste', (e) => this.handlePaste(e))
    this.inputTarget.removeEventListener('input', this.autoExpand.bind(this))
  }

  // Expanding textarea based on content
  autoExpand(event) {
    const textarea = event.target
    textarea.style.height = 'auto' // Reset height
    textarea.style.height = `${textarea.scrollHeight}px` // Set height to content
  }

  handleDragOver(event) {
    event.preventDefault()
    event.stopPropagation()
    this.formTarget.classList.add('drag-over')
  }
  
  handleDragLeave(event) {
    if (event.target === this.formTarget) {
      this.formTarget.classList.remove('drag-over')
    }
  }

  async handleDrop(event) {
    event.preventDefault()
    event.stopPropagation()
    this.formTarget.classList.remove('drag-over')
    
    // Check for files first
    const files = Array.from(event.dataTransfer.files).filter(file => 
      file.type.startsWith('image/')
    )
    
    if (files.length > 0) {
      for (const file of files) {
        await this.uploadPhoto(file)
      }
      return
    }
    
    // If no files, check for dragged images
    const items = Array.from(event.dataTransfer.items)
    for (const item of items) {
      if (item.type.indexOf('image/') !== -1) {
        const file = item.getAsFile()
        if (file) {
          await this.uploadPhoto(file)
        }
      }
    }
  }

  async handlePaste(event) {
    const items = event.clipboardData.items
    let hasImage = false
    
    for (let item of items) {
      if (item.type.indexOf("image") !== -1) {
        event.preventDefault() // Prevent default paste only if we have an image
        hasImage = true
        const file = item.getAsFile()
        await this.uploadPhoto(file)
      }
    }
    
    // If no images were found, let the default paste behavior happen
    if (!hasImage) {
      return
    }
  }

  async handleFileSelect(event) {
    const files = event.target.files
    for (let file of files) {
      await this.uploadPhoto(file)
    }
    this.fileInputTarget.value = '' // Clear the input
  }

  triggerFileInput() {
    this.fileInputTarget.click()
  }

  async uploadPhoto(file) {
    if (!file.type.startsWith('image/')) {
      showToast("Only image files are allowed", 'error')
      return
    }

    // Disable form submission during upload
    const submitButton = this.submitTarget
    submitButton.disabled = true

    // Create temporary preview with data URL
    const reader = new FileReader()
    reader.onload = (e) => {
      // Add temporary preview to uploadedPhotos
      this.uploadedPhotos.push({
        url: e.target.result,
        isLoading: true,
        tempId: Date.now() // Use this to identify the temp preview
      })
      this.updatePhotoPreview()
    }
    reader.readAsDataURL(file)

    const formData = new FormData()
    formData.append('photos', file)

    try {
      const response = await fetch(this.uploadUrlValue, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const data = await response.json()
      // Replace temporary preview with actual URLs
      this.uploadedPhotos = this.uploadedPhotos.filter(photo => !photo.isLoading)
      this.uploadedPhotos.push(...data.urls.map(url => ({ url })))
      this.updatePhotoPreview()
    } catch (error) {
      showToast("Failed to upload photo: " + error.message, 'error')
      // Remove temporary preview
      this.uploadedPhotos = this.uploadedPhotos.filter(photo => !photo.isLoading)
      this.updatePhotoPreview()
    } finally {
      // Re-enable form submission
      submitButton.disabled = false
    }
  }

  updatePhotoPreview() {
    this.previewContainerTarget.innerHTML = this.uploadedPhotos.map((photo, index) => `
      <div class="photo-preview${photo.isLoading ? ' loading' : ''}">
        <img src="${photo.url}" alt="Recipe photo ${index + 1}">
        ${photo.isLoading ? `
          <div class="upload-overlay">
            <div class="spinner-border" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>
        ` : `
          <button type="button" class="remove-photo" data-index="${index}" aria-label="Remove photo">
            <i class="bi bi-trash"></i>
          </button>
        `}
      </div>
    `).join('')

    // Add click handlers for remove buttons
    this.previewContainerTarget.querySelectorAll('.remove-photo').forEach(button => {
      button.addEventListener('click', (e) => {
        const index = parseInt(e.currentTarget.dataset.index)
        this.uploadedPhotos.splice(index, 1)
        this.updatePhotoPreview()
      })
    })
  }

  async submitForm(event) {
    event.preventDefault()
    if (this.isProcessing) return

    this.isProcessing = true
    this.submitTarget.classList.add('d-none')
    this.loadingTarget.classList.remove('d-none')
    
    try {

      const formData = new FormData()
      // Add recipe text if provided
      const recipeText = this.inputTarget.value.trim()
      if (recipeText) {
        formData.append('recipe_text_and_urls', recipeText)
      }

      // Add photo URLs to form data
      this.uploadedPhotos.forEach((photo, index) => {
        const input = document.createElement('input')
        input.type = 'hidden'
        input.name = `photo_${index}`
        input.value = photo.url
        formData.append(input.name, input.value)
      })      

      const response = await fetch(this.formTarget.action, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json',        
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
      })

      const data = await response.json()
      console.log(data)
      this.submitTarget.classList.remove('d-none')
      this.loadingTarget.classList.add('d-none')
      this.isProcessing = false
      
      if (response.ok) {
        window.location.href = data.redirect
      } else {
        throw new Error(data.message || 'Failed to import recipe')
      }
    } catch (error) {
      console.log(error)
      showToast(error.message, 'error')
      this.submitTarget.classList.remove('d-none')
      this.loadingTarget.classList.add('d-none')
      this.isProcessing = false
    }
  }
}
