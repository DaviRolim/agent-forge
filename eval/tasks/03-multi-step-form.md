Build a 4-step registration form:

1. **Personal Info:** name (required), email (required, valid format), phone (required, formatted)
2. **Address:** street, city, state (dropdown), zip code (5 digits)
3. **Preferences:** 3 checkboxes for notification preferences, 1 dropdown for preferred contact method
4. **Review & Submit:** summary of all entered data, edit buttons per section, submit button

Include field validation that blocks progression to the next step if required fields are invalid. Show inline error messages. Back/Next navigation with a progress bar. After submit, show a confirmation page with all data.

## Design Constraints
- Stack: Next.js + Tailwind CSS
- Mobile-first, responsive
- Premium feel — smooth transitions between steps
- Progress bar should animate between steps
