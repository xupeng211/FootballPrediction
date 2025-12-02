-- 队名映射SQL更新语句
-- ⚠️  请仔细检查后再执行!


-- 映射: Angers → Rangers
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Rangers'
    LIMIT 1
)
WHERE name = 'Angers';


-- 映射: Arsenal → Arsenal
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Arsenal'
    LIMIT 1
)
WHERE name = 'Arsenal';


-- 映射: Athletic Club → Athletic Club
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Athletic Club'
    LIMIT 1
)
WHERE name = 'Athletic Club';


-- 映射: Atlético Madrid → Atletico Madrid
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Atletico Madrid'
    LIMIT 1
)
WHERE name = 'Atlético Madrid';


-- 映射: Augsburg → Augsburg
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Augsburg'
    LIMIT 1
)
WHERE name = 'Augsburg';


-- 映射: Barcelona → Barcelona
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Barcelona'
    LIMIT 1
)
WHERE name = 'Barcelona';


-- 映射: Bologna → Bologna
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Bologna'
    LIMIT 1
)
WHERE name = 'Bologna';


-- 映射: Bournemouth → Bournemouth
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Bournemouth'
    LIMIT 1
)
WHERE name = 'Bournemouth';


-- 映射: Brentford → Brentford
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Brentford'
    LIMIT 1
)
WHERE name = 'Brentford';


-- 映射: Brest → Brest
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Brest'
    LIMIT 1
)
WHERE name = 'Brest';


-- 映射: Brighton → Brighton
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Brighton'
    LIMIT 1
)
WHERE name = 'Brighton';


-- 映射: Burnley → Burnley
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Burnley'
    LIMIT 1
)
WHERE name = 'Burnley';


-- 映射: Cagliari → Cagliari
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Cagliari'
    LIMIT 1
)
WHERE name = 'Cagliari';


-- 映射: Celta Vigo → Celta Vigo
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Celta Vigo'
    LIMIT 1
)
WHERE name = 'Celta Vigo';


-- 映射: Chelsea → Chelsea
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Chelsea'
    LIMIT 1
)
WHERE name = 'Chelsea';


-- 映射: Como → Como
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Como'
    LIMIT 1
)
WHERE name = 'Como';


-- 映射: Cremonese → Cremonese
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Cremonese'
    LIMIT 1
)
WHERE name = 'Cremonese';


-- 映射: Crystal Palace → Crystal Palace
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Crystal Palace'
    LIMIT 1
)
WHERE name = 'Crystal Palace';


-- 映射: Dortmund → Dortmund
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Dortmund'
    LIMIT 1
)
WHERE name = 'Dortmund';


-- 映射: Elche → Elche
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Elche'
    LIMIT 1
)
WHERE name = 'Elche';


-- 映射: Espanyol → Espanyol
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Espanyol'
    LIMIT 1
)
WHERE name = 'Espanyol';


-- 映射: Fiorentina → Fiorentina
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Fiorentina'
    LIMIT 1
)
WHERE name = 'Fiorentina';


-- 映射: Freiburg → Freiburg
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Freiburg'
    LIMIT 1
)
WHERE name = 'Freiburg';


-- 映射: Gladbach → M'gladbach
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'M''gladbach'
    LIMIT 1
)
WHERE name = 'Gladbach';


-- 映射: Hamburger SV → Hamburger SV II
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Hamburger SV II'
    LIMIT 1
)
WHERE name = 'Hamburger SV';


-- 映射: Heidenheim → FC Heidenheim
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'FC Heidenheim'
    LIMIT 1
)
WHERE name = 'Heidenheim';


-- 映射: Hellas Verona → Hellas Verona
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Hellas Verona'
    LIMIT 1
)
WHERE name = 'Hellas Verona';


-- 映射: Hoffenheim → Hoffenheim
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Hoffenheim'
    LIMIT 1
)
WHERE name = 'Hoffenheim';


-- 映射: Köln → Köln
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Köln'
    LIMIT 1
)
WHERE name = 'Köln';


-- 映射: Lazio → Lazio
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Lazio'
    LIMIT 1
)
WHERE name = 'Lazio';


-- 映射: Leeds United → Leeds
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Leeds'
    LIMIT 1
)
WHERE name = 'Leeds United';


-- 映射: Lens → Lens
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Lens'
    LIMIT 1
)
WHERE name = 'Lens';


-- 映射: Leverkusen → Leverkusen
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Leverkusen'
    LIMIT 1
)
WHERE name = 'Leverkusen';


-- 映射: Liverpool → Liverpool FC
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Liverpool FC'
    LIMIT 1
)
WHERE name = 'Liverpool';


-- 映射: Lyon → Lyon
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Lyon'
    LIMIT 1
)
WHERE name = 'Lyon';


-- 映射: Mallorca → Mallorca
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Mallorca'
    LIMIT 1
)
WHERE name = 'Mallorca';


-- 映射: Manchester City → Manchester City U18
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Manchester City U18'
    LIMIT 1
)
WHERE name = 'Manchester City';


-- 映射: Milan → Milan
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Milan'
    LIMIT 1
)
WHERE name = 'Milan';


-- 映射: Nantes → Nantes
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Nantes'
    LIMIT 1
)
WHERE name = 'Nantes';


-- 映射: Nice → Nice
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Nice'
    LIMIT 1
)
WHERE name = 'Nice';


-- 映射: Nott'ham Forest → Nottm Forest
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Nottm Forest'
    LIMIT 1
)
WHERE name = 'Nott''ham Forest';


-- 映射: RB Leipzig → RB Leipzig
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'RB Leipzig'
    LIMIT 1
)
WHERE name = 'RB Leipzig';


-- 映射: Real Sociedad → Real Sociedad
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Real Sociedad'
    LIMIT 1
)
WHERE name = 'Real Sociedad';


-- 映射: Rennes → Rennes
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Rennes'
    LIMIT 1
)
WHERE name = 'Rennes';


-- 映射: Roma → Roma
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Roma'
    LIMIT 1
)
WHERE name = 'Roma';


-- 映射: Sassuolo → Sassuolo
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Sassuolo'
    LIMIT 1
)
WHERE name = 'Sassuolo';


-- 映射: St. Pauli → St. Pauli
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'St. Pauli'
    LIMIT 1
)
WHERE name = 'St. Pauli';


-- 映射: Strasbourg → Strasbourg
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Strasbourg'
    LIMIT 1
)
WHERE name = 'Strasbourg';


-- 映射: Sunderland → Sunderland
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Sunderland'
    LIMIT 1
)
WHERE name = 'Sunderland';


-- 映射: Tottenham → Tottenham
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Tottenham'
    LIMIT 1
)
WHERE name = 'Tottenham';


-- 映射: Union Berlin → Union Berlin
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Union Berlin'
    LIMIT 1
)
WHERE name = 'Union Berlin';


-- 映射: Valencia → Valencia
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Valencia'
    LIMIT 1
)
WHERE name = 'Valencia';


-- 映射: Werder Bremen → Werder Bremen
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Werder Bremen'
    LIMIT 1
)
WHERE name = 'Werder Bremen';


-- 映射: West Ham → West Ham
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'West Ham'
    LIMIT 1
)
WHERE name = 'West Ham';


-- 映射: Wolfsburg → Wolfsburg
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Wolfsburg'
    LIMIT 1
)
WHERE name = 'Wolfsburg';


-- 映射: Wolves → Wolves
UPDATE teams
SET external_id = (
    SELECT id FROM teams
    WHERE name = 'Wolves'
    LIMIT 1
)
WHERE name = 'Wolves';

