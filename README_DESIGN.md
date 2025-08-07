# Therapy Connected Design Guidelines

## Color Palette
## Color Palette
This project uses a custom pastel-inspired palette for a modern, calming look. Use these hex codes for backgrounds, text, and accents as described below.

| Name         | Hex     | Usage                       |
|--------------|---------|-----------------------------|
| Peach        | #FFD6BA | Header, footer, blog cards  |
| Off White    | #FAF9F9 | Main background             |
| Mint         | #BEE3DB | Hero, news cards            |
| Blue Gray    | #89B0AE | Buttons, links, accents     |
| Charcoal     | #555B6E | Main text, headings, links  |

**Example Usage:**
- **Header/Footer:** Peach background (#FFD6BA), Charcoal text (#555B6E)
- **Main Background:** Off White (#FAF9F9)
- **Hero/News Cards:** Mint background (#BEE3DB), Charcoal text (#555B6E)
- **Blog Cards:** Peach background (#FFD6BA), Charcoal text (#555B6E)
- **Buttons/Links:** Blue Gray (#89B0AE) for primary actions, Charcoal (#555B6E) for secondary

Use inline `style` attributes or extend Tailwind config for these colors as needed.
- **Spacing:** Use Tailwind spacing utilities (`py-8`, `mb-4`, etc.) for whitespace.
## Buttons
- **Primary:** `bg-blue-600 text-white font-semibold rounded px-4 py-2 hover:bg-blue-700`
- **Secondary:** `bg-gray-200 text-gray-900 rounded px-4 py-2 hover:bg-gray-300`

## Forms
- **Inputs:** `border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500`
- **Labels:** `block text-sm font-medium text-gray-700 mb-1`
- **Validation:** `text-red-500 text-sm mt-1` for errors.

## Navigation
- **Navbar:** `flex items-center justify-between py-4 px-6 bg-white shadow`
- **Links:** `text-blue-600 hover:underline`

## Accessibility
- Use semantic HTML elements.
- Ensure color contrast is readable.
- All interactive elements must be keyboard accessible.

## Responsive Design
- Use Tailwind's responsive utilities (`sm:`, `md:`, `lg:`, `xl:`) for mobile-friendliness.

---

Use these guidelines and Tailwind utility classes for a clean, modern, and consistent UI. See the [Tailwind CSS documentation](https://tailwindcss.com/docs) for more options and best practices.
