from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FicheRisque(models.Model):
    _name = 'fiche.risque'
    _description = 'Fiche de risque'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouveau'))

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today,
                       tracking=True)

    declencheur = fields.Text(string='Déclencheur', required=True, tracking=True,
                              help="La cause ou l'élément à l'origine du risque.")

    liste_concernee_ids = fields.Many2many('res.partner', string='Liste concernée',
                                           tracking=True,
                                           help="Les parties prenantes affectées par le risque.")

    type_risque = fields.Selection([
        ('menace', 'Menace'),
        ('opportunite', 'Opportunité')
    ], string='Type de risque', required=True, default='menace', tracking=True)

    methode_calcul = fields.Selection([
        ('moyenne', 'Moyenne'),
        ('max', 'Maximum'),
        ('min', 'Minimum'),
        ('autre', 'Autre')
    ], string='Méthode de calcul', required=True, default='moyenne', tracking=True)

    critere_ids = fields.One2many('fiche.risque.critere', 'fiche_risque_id',
                                  string='Critères d\'évaluation')

    note_globale = fields.Float(string='Note globale', compute='_compute_note_globale',
                                store=True, readonly=True)

    niveau_risque = fields.Selection([
        ('faible', 'Faible'),
        ('moyen', 'Moyen'),
        ('eleve', 'Élevé'),
        ('critique', 'Critique')
    ], string='Niveau de risque', compute='_compute_niveau_risque', store=True)

    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('traite', 'Traité'),
        ('clos', 'Clos')
    ], string='État', default='brouillon', tracking=True)

    responsable_id = fields.Many2one('res.users', string='Responsable', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nouveau')) == _('Nouveau'):
            vals['name'] = self.env['ir.sequence'].next_by_code('fiche.risque') or _('Nouveau')
        return super(FicheRisque, self).create(vals)

    @api.depends('critere_ids.note', 'methode_calcul')
    def _compute_note_globale(self):
        for record in self:
            criteres = record.critere_ids.filtered(lambda c: c.note > 0)
            if not criteres:
                record.note_globale = 0
                continue

            notes = criteres.mapped('note')

            if record.methode_calcul == 'moyenne':
                record.note_globale = sum(notes) / len(notes)
            elif record.methode_calcul == 'max':
                record.note_globale = max(notes)
            elif record.methode_calcul == 'min':
                record.note_globale = min(notes)
            else:  # pour 'autre' ou toute autre méthode non définie
                record.note_globale = sum(notes) / len(notes)  # par défaut moyenne

    @api.depends('note_globale')
    def _compute_niveau_risque(self):
        for record in self:
            if record.note_globale <= 3:
                record.niveau_risque = 'faible'
            elif record.note_globale <= 5:
                record.niveau_risque = 'moyen'
            elif record.note_globale <= 8:
                record.niveau_risque = 'eleve'
            else:
                record.niveau_risque = 'critique'

    def action_valider(self):
        for record in self:
            if not record.critere_ids:
                raise ValidationError(_("Vous devez ajouter au moins un critère d'évaluation."))
            record.state = 'valide'

    def action_traiter(self):
        for record in self:
            record.state = 'traite'

    def action_clore(self):
        for record in self:
            record.state = 'clos'

    def action_reset(self):
        for record in self:
            record.state = 'brouillon'


class CritereEvaluation(models.Model):
    _name = 'fiche.risque.critere'
    _description = 'Critère d\'évaluation du risque'

    name = fields.Char(string='Nom du critère', required=True)
    note = fields.Integer(string='Note', required=True, default=1)
    fiche_risque_id = fields.Many2one('fiche.risque', string='Fiche de risque',
                                      ondelete='cascade')

    @api.constrains('note')
    def _check_note_range(self):
        for record in self:
            if record.note < 1 or record.note > 10:
                raise ValidationError(_("La note doit être comprise entre 1 et 10."))