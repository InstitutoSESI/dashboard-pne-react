/*
 * Device de assinatura da plataforma: os títulos escritos em forma de pergunta
 * ganham o "?" final em cor de acento (acento por seção na Educação, azul
 * institucional no PNE).
 *
 * O span permanece no fluxo do texto e SEM aria-hidden: o leitor de tela
 * continua anunciando a pergunta completa, porque a separação existe apenas
 * para pintar o glifo. Quando o texto não termina em "?" o componente devolve
 * o texto intacto, sem nó extra.
 */
export function QuestionHeading({ text }) {
  const value = typeof text === 'string' ? text.trim() : ''
  if (!value.endsWith('?')) return <>{value}</>

  return (
    <>
      {value.slice(0, -1)}
      <span className="question-heading-mark">?</span>
    </>
  )
}
