import { css } from 'lit';

export const commonStyle = css`
    :host {
        color: var(--primary-text-color);
        background: var(--lovelace-background, var(--primary-background-color));
    }

    .header {
        background-color: var(--app-header-background-color);
        color: var(--app-header-text-color, white);
        border-bottom: var(--app-header-border-bottom, none);
    }

    .toolbar {
        height: var(--header-height);
        display: flex;
        align-items: center;
        font-size: 20px;
        padding: 0 16px;
        font-weight: 400;
        box-sizing: border-box;
    }

    .main-title {
        margin: 0 0 0 24px;
        line-height: 20px;
        flex-grow: 1;
    }

    .version {
        font-size: 14px;
        font-weight: 500;
        color: rgba(var(--rgb-text-primary-color), 0.9);
    }

    .view {
        height: calc(100vh - 65px);
        display: flex;
        align-content: start;
        justify-content: center;
        flex-wrap: wrap;
        align-items: flex-start;
    }

    ha-card {
        display: block;
        margin: 5px;
    }

    .card-new {
        width: 500px;
        max-width: 500px;
    }

    .card-current {
        width: 850px;
        max-width: 850px;
    }

    ha-expansion-panel {
        --input-fill-color: none;
    }

    .form-row {
        display: flex;
        justify-content: center;
        gap: 8px;
        flex-wrap: wrap;
    }

    .form-field,
    ha-textfield,
    ha-select,
    ha-icon-picker {
        min-width: 265px;
    }

    .filler {
        flex-grow: 1;
    }

    .break {
        flex-basis: 100%;
        height: 0;
    }

    @media (max-width: 600px) {
        .form-row {
            flex-direction: column; /* Stack fields vertically */
        }

        .form-field {
            width: 100%; /* Full width */
        }

        ha-textfield,
        ha-select,
        ha-icon-picker {
            width: 100%;
            box-sizing: border-box;
        }
    }

    .task-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .task-item {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        gap: 1rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--divider-color);
    }

    .task-header {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .task-content {
        flex: 1;
    }

    .due-soon {
        color: var(--error-color, red);
        font-weight: bold;
    }

    .warning {
        --mdc-theme-primary: var(--error-color);
        color: var(--primary-text-color);
    }

    .form-actions {
        display: flex;
        gap: 12px;
        justify-content: flex-end;
        align-items: center;
        margin-top: 16px;
    }

    .action-button {
        appearance: none;
        border: none;
        border-radius: 999px;
        min-height: 40px;
        padding: 0 18px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        font: inherit;
        font-weight: 600;
        cursor: pointer;
        transition: transform 120ms ease, opacity 120ms ease;
    }

    .action-button:hover {
        transform: translateY(-1px);
    }

    .primary-button {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
        box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.18));
    }

    .secondary-button {
        background: color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color) 88%);
        color: var(--primary-text-color);
        border: 1px solid color-mix(in srgb, var(--primary-color) 24%, transparent 76%);
    }

    .action-button ha-svg-icon {
        width: 18px;
        height: 18px;
        display: inline-flex;
    }

    @media (max-width: 600px) {
        .form-actions {
            flex-direction: column;
            align-items: stretch;
        }

        .action-button {
            width: 100%;
        }
    }

    ha-dialog {
        --mdc-dialog-min-width: 600px;
    }

    @media (max-width: 600px) {
        ha-dialog {
        --mdc-dialog-min-width: auto;
        }
    }
`;
