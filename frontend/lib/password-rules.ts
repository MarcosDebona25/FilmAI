const SPECIAL = "@#$%&*!";

export type PasswordRules = Record<"length" | "case" | "number" | "symbol", boolean>;

/** Las cuatro reglas de la lista de requisitos del registro (doc 04). */
export function passwordRules(password: string): PasswordRules {
  return {
    length: password.length >= 8 && password.length <= 20,
    case: /\p{Ll}/u.test(password) && /\p{Lu}/u.test(password),
    number: /\d/.test(password),
    symbol: [...password].some((char) => SPECIAL.includes(char)),
  };
}
