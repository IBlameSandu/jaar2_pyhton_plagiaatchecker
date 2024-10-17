from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import libcst as cst
from spellchecker import SpellChecker
import ast

class CommentCollector(cst.CSTVisitor):
  def __init__(self):
    self.comment_set=set()

  def visit_Comment(self, node: cst.Comment) -> None:
    self.comment_set.add(node.value.lstrip("#.!?").strip())

class LexiconCollector(cst.CSTVisitor):
  def __init__(self):
     self.volle_inhoud=[]
     self.alle_namen=[]

  def visit_SimpleString(self, node: cst.SimpleString) -> None:
    self.volle_inhoud.append(ast.literal_eval(node.value))
  def visit_Name(self, node: cst.Name) -> None:
    self.alle_namen.append(node.value)

class CommentRemover(cst.CSTTransformer):
  def leave_Comment(self, node:cst.Comment, updated_node=cst.Comment):
    return cst.RemoveFromParent()
  
def getAutheurs(invoer):
    """Gaat zien of de opgegeven pad effectief een map is, als dat wel is gaat het de namen van alles dat erin is opslagen.
    Als dat niet is wordt -1 gereturned."""
    p=Path(invoer)
    if p.is_dir():
      gevonden = [x.name for x in p.iterdir() if x.is_dir()] 
      return gevonden
    else:
      print(f"Dit is geen directory.")
      exit()
    
def getFiles(invoer, autheurs):  
  gesorteerdeFiles={}
  for x in autheurs:
    p=Path(f"{invoer}/{x}")
    files=list(p.glob("*.py"))
    gesorteerdeFiles[x]=[f.name for f in files]
  return gesorteerdeFiles

def getComments(inhoud):
  """Maakt een visitor en haalt de comments op."""
  visitor=CommentCollector()
  inhoud.visit(visitor)
  return visitor.comment_set

def getStringsEnInhoud(inhoud):
  """Maakt een visitor en haalt de inhoud en de namen op."""
  visitor=LexiconCollector()
  inhoud.visit(visitor)
  return visitor.volle_inhoud, visitor.alle_namen

def getSpellFouten(volle_inhoud):
  spell=SpellChecker()
  fouten=spell.unknown(volle_inhoud)
  return fouten

def removeComments(cstInhoud):  
  transformer=CommentRemover()  
  return cstInhoud.visit(transformer)

def normaliseerCode(inhoud):
  astinhoud=ast.parse(inhoud)
  genormaliseerde_code=ast.unparse(astinhoud)
  return genormaliseerde_code


if __name__=="__main__":
    invoer=input("welke directory moet ik bekijken?\n") #pad invoer

    autheurs: list = getAutheurs(invoer)
    files: dict = getFiles(invoer,autheurs)
    echte_namen_autheurs : dict[str, dict[str, list]] = {auth1: {auth2:[] for auth2 in autheurs[a+1:]} for a,auth1 in enumerate(autheurs) if a != len(autheurs)-1}
    anonimisatie_autheurs: dict = {autheurs[x]: f"autheur{x+1}" for x in range(len(autheurs))}
    print(anonimisatie_autheurs)

    for autheur1 in echte_namen_autheurs:
        for file in files[autheur1]:
          inhoud_auth1=Path(f"{invoer}/{autheur1}/{file}").read_text().strip()

          cst_inhoud_auth1=cst.parse_module(inhoud_auth1)
          genormaliseerde_code_auth1=normaliseerCode(inhoud_auth1)
          comments1=getComments(cst_inhoud_auth1)
          simpleString_inhoud_auth1, namen_inhoud_auth1=getStringsEnInhoud(cst_inhoud_auth1)
          fouten_auth1=set(getSpellFouten(simpleString_inhoud_auth1))
          fouten_auth1.update(getSpellFouten(namen_inhoud_auth1))
          cst_inhoud_auth1_zonder_comments=removeComments(cst_inhoud_auth1)

          for autheur2 in echte_namen_autheurs[autheur1]:
              for file2 in files[autheur2]:
                inhoud_auth2=Path(f"{invoer}/{autheur2}/{file2}").read_text().strip()

                cst_inhoud_auth2=cst.parse_module(inhoud_auth2)
                genormaliseerde_code_auth2=normaliseerCode(inhoud_auth2)
                comments2=getComments(cst_inhoud_auth2)

                if inhoud_auth1==inhoud_auth2:
                  echte_namen_autheurs[autheur1][autheur2].append("identieke files")
                
                overeenkomstige_comments=comments1&comments2
                for comment in overeenkomstige_comments:
                  echte_namen_autheurs[autheur1][autheur2].append(f"identieke comment: {comment}")

                simpleString_inhoud_auth2, namen_inhoud_auth2=getStringsEnInhoud(cst_inhoud_auth2)
                fouten_auth2=set(getSpellFouten(simpleString_inhoud_auth2))
                fouten_auth2.update(getSpellFouten(namen_inhoud_auth2))
                overeenkomstige_namen=set(namen_inhoud_auth1)&set(namen_inhoud_auth2)
                overeenkomstige_fouten=fouten_auth1&fouten_auth2

                if simpleString_inhoud_auth1==simpleString_inhoud_auth2:
                  echte_namen_autheurs[autheur1][autheur2].append(f"identieke simplestrings")
                for naam in overeenkomstige_namen:
                  echte_namen_autheurs[autheur1][autheur2].append(f"identieke naam: {naam}")
                for fout in overeenkomstige_fouten:
                  echte_namen_autheurs[autheur1][autheur2].append(f"identieke spelfout: {fout}")
                
                cst_inhoud_auth2_zonder_comments=removeComments(cst_inhoud_auth2)
              
                if cst_inhoud_auth1_zonder_comments.deep_equals(cst_inhoud_auth2_zonder_comments):
                  echte_namen_autheurs[autheur1][autheur2].append("identiek op de comments na")
                if genormaliseerde_code_auth1 == genormaliseerde_code_auth2 and "identiek op de comments na" not in echte_namen_autheurs[autheur1][autheur2]:
                  echte_namen_autheurs[autheur1][autheur2].append("identieke abstracte syntaxbomen")

    env = Environment(
        loader=FileSystemLoader("."),
        autoescape=select_autoescape()
    )

    my_template = env.get_template("index.html.jinja")

    with open("index.html", "w") as f: f.write(my_template.render(
        combinaties=echte_namen_autheurs,
        autheurs=autheurs,
        anonimisatie=anonimisatie_autheurs
    ))