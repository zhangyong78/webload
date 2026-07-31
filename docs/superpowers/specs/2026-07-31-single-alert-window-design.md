# Single Alert Window Design

## Goal

Prevent unattended reminder popups from creating nested modal windows while keeping email, system notifications, and scheduled checks independent.

## Design

- Replace the static blocking `QMessageBox.information` call with one reusable, non-modal `QMessageBox` owned by `AlertPopupController`.
- A new alert updates the same dialog with the latest title and message.
- While the dialog remains open, its informative text shows how many alerts have arrived.
- Closing the dialog resets the visible alert count. The same dialog object is reused for later reminders.
- Email dispatch remains before popup display, and existing popup enable/disable configuration remains unchanged.

## Verification

- Showing two alerts returns the same dialog object.
- The dialog is non-modal and displays the latest message plus a count of two.
- Closing the dialog resets the count for the next alert.
- Existing email-before-popup behavior remains covered.
- The complete test suite and Windows package build must pass.
