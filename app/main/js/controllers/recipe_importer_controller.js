import { Controller } from '@hotwired/stimulus'
import { showToast } from '../../../static/js/utils/toast'

export default class extends Controller {
  static targets = ['input', 'form', 'submit', 'loading', 'dropzone', 'fileInput', 'previewContainer', 'error']
  
  // Configuration
  static values = {
    maxFileSize: { type: Number, default: 10 * 1024 * 1024 }, // 10MB
    maxFiles: { type: Number, default: 5 },
    uploadUrl: String
  }

  connect() {
    console.log('RecipeImporter controller connected')
    this.setupPasteListener()
    this.uploadedPhotos = []
  }

  setupPasteListener() {
    document.addEventListener('paste', (e) => this.handlePaste(e))
  }

  async submitForm(event) {
    event.preventDefault()
    console.log('Submit form called')
    const url = this.inputTarget.value.trim()

    console.log('URL:', url)
    console.log('Uploaded photos:', this.uploadedPhotos)

    if (!url && this.uploadedPhotos.length === 0) {
      showToast('Please enter a recipe URL or add photos', 'warning')
      return
    }

    // Show loading state
    this.submitTarget.classList.add('d-none')
    this.loadingTarget.classList.remove('d-none')

    // Get the form data
    const formData = new FormData(this.formTarget)
    
    // Add photo URLs
    this.uploadedPhotos.forEach((url, index) => {
      formData.append(`photo_${index}`, url)
    })

    // Log form data
    for (let [key, value] of formData.entries()) {
      console.log(`${key}: ${value}`)
    }

    // Submit form via AJAX
    try {
      const response = await fetch(this.formTarget.action, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value
        },
        body: formData
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.message || 'Failed to import recipe')
      }

      showToast(data.message, data.status)
      window.location.href = data.redirect
    } catch (error) {
      showToast(error.message || 'An error occurred while importing the recipe', 'error')
      this.resetFormState()
    }
  }

  resetFormState() {
    this.submitTarget.classList.remove('d-none')
    this.loadingTarget.classList.add('d-none')
    this.errorTarget.classList.add('d-none')
  }

  handleDragOver(e) {
    e.preventDefault()
    this.dropzoneTarget.classList.add('drag-active')
  }

  handleDragEnter(e) {
    e.preventDefault()
    this.dropzoneTarget.classList.add('drag-active')
  }

  handleDragLeave(e) {
    e.preventDefault()
    this.dropzoneTarget.classList.remove('drag-active')
  }

  handleDrop(e) {
    e.preventDefault()
    this.dropzoneTarget.classList.remove('drag-active')
    const files = e.dataTransfer.files
    this.handleFiles(files)
  }

  handlePaste(e) {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items
    const files = []
    
    for (const item of items) {
      if (item.type.indexOf('image') === 0) {
        const file = item.getAsFile()
        files.push(file)
      }
    }
    
    if (files.length > 0) {
      this.handleFiles(files)
    }
  }

  handleFileSelect(e) {
    const files = e.target.files
    this.handleFiles(files)
  }

  triggerFileInput() {
    this.fileInputTarget.click()
  }

  async handleFiles(files) {
    // Check total number of files
    const currentCount = this.previewContainerTarget.children.length
    const newCount = currentCount + files.length
    if (newCount > this.maxFilesValue) {
      showToast(`You can only upload up to ${this.maxFilesValue} photos`, 'warning')
      return
    }

    for (const file of files) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        showToast('Please upload only image files', 'warning')
        continue
      }

      // Validate file size
      if (file.size > this.maxFileSizeValue) {
        showToast(`File ${file.name} is too large. Maximum size is ${this.maxFileSizeValue / (1024 * 1024)}MB`, 'warning')
        continue
      }

      try {
        // Upload the file first
        const formData = new FormData()
        formData.append('photos', file)

        const response = await fetch(this.uploadUrlValue, {
          method: 'POST',
          headers: {
            'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value
          },
          body: formData
        })

        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.error || 'Failed to upload photo')
        }

        // Add the URL to our list
        this.uploadedPhotos.push(data.urls[0])
        
        // Create preview
        const preview = document.createElement('div')
        preview.className = 'photo-preview'
        preview.innerHTML = `
          <img src="${data.urls[0]}" alt="Recipe photo">
          <button type="button" class="btn-remove" data-action="click->recipe-importer#removePhoto">
            <i class="bi bi-x-circle"></i>
          </button>
        `
        this.previewContainerTarget.appendChild(preview)
      } catch (error) {
        showToast(error.message || 'Failed to upload photo', 'error')
      }
    }
  }

  removePhoto(e) {
    const preview = e.target.closest('.photo-preview')
    const img = preview.querySelector('img')
    const index = Array.from(this.previewContainerTarget.children).indexOf(preview)
    this.uploadedPhotos.splice(index, 1)
    preview.remove()
  }
}
