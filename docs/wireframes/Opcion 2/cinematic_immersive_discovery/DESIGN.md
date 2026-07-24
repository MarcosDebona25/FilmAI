---
name: Cinematic Immersive Discovery
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#d1c5ac'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#9a9078'
  outline-variant: '#4e4633'
  surface-tint: '#f0c110'
  primary: '#ffe5a0'
  on-primary: '#3d2f00'
  primary-container: '#f5c518'
  on-primary-container: '#695200'
  inverse-primary: '#745b00'
  secondary: '#c6c4df'
  on-secondary: '#2f2e43'
  secondary-container: '#47475d'
  on-secondary-container: '#b8b6d0'
  tertiary: '#bdefff'
  on-tertiary: '#003641'
  tertiary-container: '#49dbff'
  on-tertiary-container: '#005e70'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffe08b'
  primary-fixed-dim: '#f0c110'
  on-primary-fixed: '#241a00'
  on-primary-fixed-variant: '#584400'
  secondary-fixed: '#e2e0fc'
  secondary-fixed-dim: '#c6c4df'
  on-secondary-fixed: '#1a1a2e'
  on-secondary-fixed-variant: '#45455b'
  tertiary-fixed: '#b0ecff'
  tertiary-fixed-dim: '#42d7fb'
  on-tertiary-fixed: '#001f27'
  on-tertiary-fixed-variant: '#004e5e'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Playfair Display
    fontSize: 56px
    fontWeight: '700'
    lineHeight: 64px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Playfair Display
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-sm:
    fontFamily: Playfair Display
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 64px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style

The design system is engineered to evoke the atmosphere of a premium cinema. The personality is **Professional, Immersive, and Modern**, prioritizing content discovery through a "theatrical" interface. 

The style utilizes **Minimalism** with a **Glassmorphic** twist to maintain depth without clutter. High-quality imagery is the protagonist, supported by a sophisticated UI that recedes to let cinematography shine. This is achieved through dark surfaces, crisp typography, and intentional use of motion to guide the user through vast libraries of media.

## Colors

The palette is anchored in a **Dark Mode** default to reduce eye strain and maximize the vibrancy of movie posters and trailers. 

- **Primary Background (#121212):** Used for the base layer to create a "black box" theater effect.
- **Secondary Surface (#1A1A2E):** A deep midnight navy used for cards, sidebars, and elevated containers to provide subtle separation.
- **Accent Gold (#F5C518):** Reserved for high-priority actions, ratings, and "Pro" features. It ensures WCAG 2.1 AA compliance against the dark backgrounds.
- **Accent Orange (#E67E22):** Used for secondary highlights, trending indicators, or genre badges.
- **Hierarchy:** Pure white (#FFFFFF) is used exclusively for titles and primary labels, while grays provide secondary and tertiary context to prevent visual fatigue.

## Typography

This design system uses a dual-font strategy to balance editorial elegance with functional clarity.

- **Editorial Titles:** `Playfair Display` is used for movie titles, section headers, and featured hero components. It provides a "cinematic touch" that differentiates the platform from generic SaaS tools.
- **System UI:** `Inter` is used for all functional text, including metadata (durations, years), navigation, descriptions, and buttons. 
- **Scale:** Larger display sizes scale down significantly for mobile to ensure hero sections remain readable without excessive scrolling.
- **Readability:** Line heights for body text are generous (1.5x) to ensure legibility against high-contrast dark backgrounds.

## Layout & Spacing

The system follows a strict **8px base grid** to maintain mathematical harmony.

- **Grid Model:** A 12-column fluid grid is used for desktop (max-width 1440px). On mobile, this collapses to a 4-column grid.
- **Rhythm:** Spacing between related items (e.g., a movie title and its metadata) uses `xs` or `sm`. Spacing between distinct sections uses `xl` or `xxl`.
- **Responsive Behavior:** 
  - **Desktop:** Wide margins (`48px`) to allow the interface to breathe. 
  - **Tablet:** Content reflows to 3 columns for card grids; margins reduce to `24px`.
  - **Mobile:** Horizontal swiping "carousels" are preferred over vertical stacks for genre rows to save vertical space.

## Elevation & Depth

Depth is communicated through **Tonal Layers** and **Backdrop Blurs** rather than traditional heavy drop shadows.

- **Level 0 (Base):** #121212. Used for the main canvas.
- **Level 1 (Surface):** #1A1A2E. Used for cards and secondary navigation panels.
- **Level 2 (Floating):** Semi-transparent glass (rgba(26, 26, 46, 0.8)) with a 12px blur. Used for fixed navigation bars and overlays.
- **Focus States:** High-visibility 2px solid strokes using the Accent Gold (#F5C518) ensure that keyboard navigation is clear and accessible.
- **Shadows:** When used for modal dialogs, shadows are ultra-diffused: `0 20px 40px rgba(0,0,0,0.6)`.

## Shapes

The shape language varies slightly by component type to create a visual hierarchy of "clickability":

- **Cards:** 8px (rounded) to feel substantial and modern.
- **Buttons:** 6px (custom) to provide a tighter, more professional appearance.
- **Inputs:** 4px (soft) to emphasize precision and utility.
- **Avatars/Badges:** Fully rounded (pill/circle) for distinct identification.

Visual interest is added via a **Subtle Hover Scale**: movie cards scale by 1.05x on hover to provide immediate interactive feedback.

## Components

### Buttons
- **Primary:** Background #F5C518, Text #121212. Bold, high contrast.
- **Secondary:** Outlined 1px #FFFFFF, Text #FFFFFF.
- **Ghost:** No background, Text #B0B0B0.
- **Danger:** Background #E74C3C (standard utility red), Text #FFFFFF.

### Cards
- **Movie Card:** 8px radius. Aspect ratio 2:3. Contains a gradient overlay at the bottom to ensure white metadata text is readable over varied poster art.
- **Interaction:** On hover, apply a `1.05x` scale and increase brightness of the border.

### Inputs
- **Search/Fields:** 4px radius. Background #1A1A2E with a 1px #333333 border. Focus state changes border to #F5C518.

### Navigation
- **Top Nav:** Fixed, glassmorphic blur. Active states indicated by an Accent Gold underline or text color change.
- **Chatbot FAB:** Circular button in the bottom-right. Background #F5C518, Icon #121212. Elevated with a soft ambient shadow.

### Chips
- **Genre Chips:** 12px font size, uppercase. Dark gray background with subtle hover states. Used for categorizing content without distracting from the title.