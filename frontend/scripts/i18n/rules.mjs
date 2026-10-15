// Excepciones temporales: se eliminan al integrar cada diseño definitivo.
export const legacyFiles = ["components/NavigationGuard.tsx"];
const visibleAttributes = new Set([
  "aria-label",
  "alt",
  "placeholder",
  "title",
  "label",
  "description",
]);
export const rules = {
  "no-visible-literals": {
    meta: {
      type: "problem",
      schema: [],
      messages: { literal: "Usá una clave del catálogo para el texto visible." },
    },
    create(context) {
      function visible(node) {
        if (!node) return;
        if (
          node.type === "Literal" &&
          typeof node.value === "string" &&
          /\p{L}/u.test(node.value) &&
          node.value !== "FilmAI"
        ) {
          context.report({ node, messageId: "literal" });
        } else if (
          node.type === "TemplateLiteral" &&
          node.quasis.some((part) => /\p{L}/u.test(part.value.cooked ?? ""))
        ) {
          context.report({ node, messageId: "literal" });
        } else if (node.type === "ConditionalExpression") {
          visible(node.consequent);
          visible(node.alternate);
        } else if (
          node.type === "LogicalExpression" ||
          (node.type === "BinaryExpression" && node.operator === "+")
        ) {
          visible(node.left);
          visible(node.right);
        }
      }
      return {
        JSXText(node) {
          if (/[\p{L}]/u.test(node.value) && node.value.trim() !== "FilmAI")
            context.report({ node, messageId: "literal" });
        },
        JSXAttribute(node) {
          if (visibleAttributes.has(node.name.name) && node.value?.type === "Literal")
            visible(node.value);
        },
        JSXExpressionContainer(node) {
          if (node.parent.type !== "JSXAttribute" || visibleAttributes.has(node.parent.name.name))
            visible(node.expression);
        },
        CallExpression(node) {
          if (
            node.callee.type === "MemberExpression" &&
            node.callee.object.name === "toast" &&
            ["Literal", "TemplateLiteral"].includes(node.arguments[0]?.type)
          )
            context.report({ node: node.arguments[0], messageId: "literal" });
        },
      };
    },
  },
  "no-debug": {
    meta: {
      type: "problem",
      schema: [],
      messages: { debug: "El frontend nunca consume diagnósticos debug." },
    },
    create(context) {
      return {
        Property(node) {
          if (
            node.parent.type === "ObjectPattern" &&
            (node.key.name === "debug" || node.key.value === "debug")
          )
            context.report({ node, messageId: "debug" });
        },
        MemberExpression(node) {
          if (node.property.name === "debug" || node.property.value === "debug")
            context.report({ node, messageId: "debug" });
        },
      };
    },
  },
  "centralized-formats": {
    meta: {
      type: "problem",
      schema: [],
      messages: { format: "Centralizá Intl y toLocale* en lib/format.ts." },
    },
    create(context) {
      return {
        MemberExpression(node) {
          if (
            node.object.name === "Intl" ||
            /^toLocale/.test(node.property.name ?? node.property.value ?? "")
          )
            context.report({ node, messageId: "format" });
        },
      };
    },
  },
};
