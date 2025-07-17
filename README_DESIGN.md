# Therapy Connected Design Guidelines

## Color Palette
- **Lightest:** `#E8E9F3` (backgrounds, subtle sections)
- **Light Gray:** `#CECECE` (borders, muted backgrounds)
- **Medium Gray:** `#A6A6A8` (secondary text, icons)
- **Dark:** `#272635` (main text, headings, nav)
- **Accent Blue:** `#B1E5F2` (buttons, highlights, links)

## Typography
- **Font:** Tailwind's default `font-sans`.
- **Headings:** `font-bold`, `text-2xl` and up for titles.
- **Body:** `text-base` for normal text, `text-sm` for captions.

## Layout
- **Container:** `max-w-4xl mx-auto px-4` for main content.
- **Spacing:** Use Tailwind spacing utilities (`py-8`, `mb-4`, etc.) for whitespace.
- **Cards:** `rounded-lg shadow bg-white p-6` for card components.

## Buttons
- **Primary:** `bg-[#B1E5F2] text-[#272635] font-semibold rounded px-4 py-2 hover:bg-[#A6A6A8]`
- **Secondary:** `bg-[#CECECE] text-[#272635] rounded px-4 py-2 hover:bg-[#A6A6A8]`

## Forms
- **Inputs:** `border border-[#CECECE] rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#B1E5F2]`
- **Labels:** `block text-sm font-medium text-[#272635] mb-1`
- **Validation:** `text-rose-500 text-sm mt-1` for errors.

## Navigation
- **Navbar:** `flex items-center justify-between py-4 px-6 bg-[#E8E9F3] shadow`
- **Links:** `text-[#B1E5F2] hover:underline`

## Accessibility
- Use semantic HTML elements.
- Ensure color contrast is readable.
- All interactive elements must be keyboard accessible.

## Responsive Design
- Use Tailwind's responsive utilities (`sm:`, `md:`, `lg:`, `xl:`) for mobile-friendliness.

---

Use these guidelines and Tailwind utility classes for a clean, modern, and consistent UI. See the [Tailwind CSS documentation](https://tailwindcss.com/docs) for more options and best practices.
